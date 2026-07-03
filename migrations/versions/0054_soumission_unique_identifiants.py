# ruff: noqa: E501 - migrations carry long SQL and seeded text lines
"""Single-submission modification cycle, staged photo, durable identifiers.

1. membre.photo_pending_url / photo_pending_phash: a replacement identity photo
   is STAGED (never overwrites the live photo) and is only promoted to the
   official photo when the administration validates the modification request.
   This makes the photo part of the same single business submission as the text
   fields, instead of a separate immediate write.

2. modification_membre single-pending guarantee: the resubmission bug left
   several 'en_attente' proposals per request (production had a real case). We
   keep the most recent proposal per request and drop the superseded duplicates,
   then a partial unique index makes more than one pending proposal per request
   impossible at the database level (idempotence backstop).

3. Durable, non-saturating identifiers, year-partitioned with an atomic counter:
   - matricule_compteur: new members get ADS-YYYY-NNNNNN (six digits reset every
     year, so the space never saturates; concurrency-safe via a single
     UPSERT ... RETURNING). Existing ADS-NNNNNN matricules are LEFT UNTOUCHED and
     coexist (different shape, no collision).
   - demande.reference (DEM-YYYY-NNNNNN) with demande_compteur: the display
     reference gains a year component and a per-year counter. Existing requests
     are backfilled from their year and existing global numero (kept as the
     intra-year number, so their identity is preserved); the current year's
     counter is seeded above the highest existing number to avoid any collision.

Revision ID: 0054_soumission_unique_identifiants
Revises: 0053_deblocage_lecture
Create Date: 2026-07-04
"""
from __future__ import annotations

from alembic import op

revision = "0054_soumission_ids"
down_revision = "0053_deblocage_lecture"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Staged replacement photo (promoted only at admin validation).
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS photo_pending_url text")
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS photo_pending_phash text")

    # 2. Deduplicate superseded 'en_attente' proposals (resubmission bug cleanup),
    #    keeping the most recent per request, then forbid more than one pending.
    op.execute(
        """
        DELETE FROM modification_membre m
        USING (
            SELECT id, row_number() OVER (
                PARTITION BY demande_id ORDER BY propose_le DESC, id DESC
            ) AS rn
            FROM modification_membre
            WHERE statut = 'en_attente' AND demande_id IS NOT NULL
        ) d
        WHERE m.id = d.id AND d.rn > 1
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_modification_membre_demande_attente "
        "ON modification_membre (demande_id) WHERE statut = 'en_attente' AND demande_id IS NOT NULL"
    )

    # 3a. Matricule year counter (new ADS-YYYY-NNNNNN format).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS matricule_compteur (
            annee integer PRIMARY KEY,
            dernier bigint NOT NULL DEFAULT 0
        )
        """
    )

    # 3b. Demande reference (DEM-YYYY-NNNNNN) plus its year counter.
    op.execute("ALTER TABLE demande ADD COLUMN IF NOT EXISTS reference text")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS demande_compteur (
            annee integer PRIMARY KEY,
            dernier bigint NOT NULL DEFAULT 0
        )
        """
    )
    # Seed each year's counter above the highest existing number for that year.
    op.execute(
        """
        INSERT INTO demande_compteur (annee, dernier)
        SELECT extract(year FROM cree_le)::int AS annee, COALESCE(max(numero), 0) AS dernier
        FROM demande
        WHERE numero IS NOT NULL
        GROUP BY 1
        ON CONFLICT (annee) DO UPDATE SET dernier = GREATEST(demande_compteur.dernier, EXCLUDED.dernier)
        """
    )
    # Backfill existing requests: DEM-{year}-{numero zero-padded}. numero is
    # globally unique, so the whole reference is unique.
    op.execute(
        """
        UPDATE demande
        SET reference = 'DEM-' || extract(year FROM cree_le)::int || '-' || lpad(numero::text, 6, '0')
        WHERE reference IS NULL AND numero IS NOT NULL
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_demande_reference ON demande (reference) WHERE reference IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_demande_reference")
    op.execute("ALTER TABLE demande DROP COLUMN IF EXISTS reference")
    op.execute("DROP TABLE IF EXISTS demande_compteur")
    op.execute("DROP TABLE IF EXISTS matricule_compteur")
    op.execute("DROP INDEX IF EXISTS ux_modification_membre_demande_attente")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS photo_pending_phash")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS photo_pending_url")
