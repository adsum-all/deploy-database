# ruff: noqa: E501 - migrations carry long SQL lines
"""Multiple functions per member (a member can hold several responsibilities).

A member can hold zero, one or several functions at the same time (e.g. head of a
commission AND referent AND a particular protocol), independently from the
consecration title (Berger/Bergere). Until now membre carried a single
fonction_cle; this adds membre_fonction so functions are true, changeable,
cumulable records.

- fonction_cle: the function type (references fonction_honorifique by key, plain
  text like membre.fonction_cle, resolved by LEFT JOIN so a function type is never
  hard-locked).
- perimetre: the scope (Commission KERUBIM, Mission Timothe, coordinateurs Afrique...).
- confirmee: publicly shown once an admin confirms it.
- actif: currently held (a past function can be kept with actif=false + date_fin).
- principale: the primary function, mirrored back to membre.fonction_cle so every
  existing display (titre prefix, scan) keeps working with no change.
- ordre: display order when several functions are shown.

Existing single functions are migrated into the table as the principal function.
The legacy membre.fonction_cle / fonction_confirmee / fonction_perimetre columns
are KEPT as a denormalised mirror of the principal function (no breakage).

Revision ID: 0059_membre_fonction_multi
Revises: 0058_consecration_confidentiel
Create Date: 2026-07-04
"""
from __future__ import annotations

from alembic import op

revision = "0059_membre_fonction_multi"
down_revision = "0058_consecration_confidentiel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS membre_fonction (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            membre_id uuid NOT NULL REFERENCES membre(id) ON DELETE CASCADE,
            fonction_cle text NOT NULL,
            perimetre text,
            confirmee boolean NOT NULL DEFAULT true,
            actif boolean NOT NULL DEFAULT true,
            principale boolean NOT NULL DEFAULT false,
            ordre integer NOT NULL DEFAULT 100,
            date_debut date,
            date_fin date,
            cree_le timestamptz NOT NULL DEFAULT now(),
            maj_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_membre_fonction_membre ON membre_fonction (membre_id, actif, ordre)")
    op.execute('ALTER TABLE IF EXISTS public."membre_fonction" ENABLE ROW LEVEL SECURITY')
    # Migrate the existing single function into the table as the principal one.
    op.execute(
        """
        INSERT INTO membre_fonction (membre_id, fonction_cle, perimetre, confirmee, actif, principale, ordre)
        SELECT id, fonction_cle, fonction_perimetre, coalesce(fonction_confirmee, false), true, true, 0
        FROM membre
        WHERE fonction_cle IS NOT NULL AND fonction_cle <> ''
          AND NOT EXISTS (SELECT 1 FROM membre_fonction mf WHERE mf.membre_id = membre.id)
        """
    )
    # Berger/Bergere is a consecration TITLE, not a function: move any such entry
    # to the consecration title and remove it from the function list, so the two
    # concepts are never confused.
    op.execute(
        "UPDATE membre SET est_berger = true WHERE id IN "
        "(SELECT membre_id FROM membre_fonction WHERE lower(fonction_cle) IN ('berger', 'bergere')) "
        "OR lower(coalesce(fonction_cle, '')) IN ('berger', 'bergere')"
    )
    op.execute("DELETE FROM membre_fonction WHERE lower(fonction_cle) IN ('berger', 'bergere')")
    op.execute(
        "UPDATE membre SET fonction_cle = NULL, fonction_confirmee = false, fonction_perimetre = NULL "
        "WHERE lower(coalesce(fonction_cle, '')) IN ('berger', 'bergere')"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS membre_fonction")
