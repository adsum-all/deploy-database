# ruff: noqa: E501 - migrations carry long SQL lines
"""Internal-communication "Information" broadcasts to members.

An Information is a one-way institutional communication (not a conversation): an
administrator publishes a titled message, at a priority level (normale/importante/
urgente), to a targeted audience resolved from the existing destination referential
(cible_activite), and each recipient's delivery is tracked (envoye -> lu -> confirme).
Members consult these in a permanent "Informations" feed.

Two tables:
- ``information``: the broadcast itself (content, priority, schedule, expiry, pin,
  optional media/link/action, ack requirement). Optional media columns are created
  now so later slices (audio note, cover image, document) need no new migration.
- ``information_destinataire``: one row per recipient, the delivery/read/confirm
  state, unique per (information, membre) so a member is never duplicated across
  overlapping target segments.

RLS mirrors 0151: readable by the authenticated roles, writable by administrators;
the API connects as the schema owner and enforces the per-member scope in code.

Revision ID: 0154_informations
Revises: 0153_membre_cheminement
Create Date: 2026-07-18
"""
from __future__ import annotations

from alembic import op

revision = "0154_informations"
down_revision = "0153_membre_cheminement"
branch_labels = None
depends_on = None

_LECTURE = "ARRAY['super_admin', 'admin', 'gestionnaire', 'direction', 'membre', 'controleur']::text[]"
_ECRITURE = "ARRAY['super_admin', 'admin', 'gestionnaire']::text[]"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS information (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            titre text NOT NULL,
            sous_titre text,
            contenu text NOT NULL DEFAULT '',
            priorite text NOT NULL DEFAULT 'normale',
            auteur text,
            statut text NOT NULL DEFAULT 'brouillon',
            publier_le timestamptz,
            expire_le timestamptz,
            epingle_jusqu timestamptz,
            requiert_accuse boolean NOT NULL DEFAULT false,
            lecture_vocale_auto boolean NOT NULL DEFAULT true,
            lien_url text,
            action_label text,
            action_url text,
            audio_url text,
            image_url text,
            document_url text,
            cibles jsonb NOT NULL DEFAULT '[]'::jsonb,
            cree_par uuid REFERENCES utilisateur(id),
            cree_le timestamptz NOT NULL DEFAULT now(),
            maj_le timestamptz NOT NULL DEFAULT now(),
            envoye_le timestamptz,
            CONSTRAINT information_priorite_chk CHECK (priorite IN ('normale', 'importante', 'urgente')),
            CONSTRAINT information_statut_chk CHECK (statut IN ('brouillon', 'programme', 'envoye', 'archive'))
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_information_statut ON information (statut, cree_le DESC)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS information_destinataire (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            information_id uuid NOT NULL REFERENCES information(id) ON DELETE CASCADE,
            membre_id uuid NOT NULL REFERENCES membre(id) ON DELETE CASCADE,
            statut text NOT NULL DEFAULT 'envoye',
            lu_le timestamptz,
            confirme_le timestamptz,
            cree_le timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT information_dest_statut_chk CHECK (statut IN ('prepare', 'envoye', 'lu', 'confirme', 'echec')),
            CONSTRAINT information_dest_unique UNIQUE (information_id, membre_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_information_dest_membre ON information_destinataire (membre_id, statut)")

    for table in ("information", "information_destinataire"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS {table}_select ON {table}")
        op.execute(f"CREATE POLICY {table}_select ON {table} FOR SELECT USING (adsum_current_role() = ANY({_LECTURE}))")
        op.execute(f"DROP POLICY IF EXISTS {table}_write ON {table}")
        op.execute(f"CREATE POLICY {table}_write ON {table} FOR ALL USING (adsum_current_role() = ANY({_ECRITURE})) WITH CHECK (adsum_current_role() = ANY({_ECRITURE}))")


def downgrade() -> None:
    for table in ("information_destinataire", "information"):
        op.execute(f"DROP POLICY IF EXISTS {table}_write ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_select ON {table}")
    op.execute("DROP TABLE IF EXISTS information_destinataire")
    op.execute("DROP TABLE IF EXISTS information")
