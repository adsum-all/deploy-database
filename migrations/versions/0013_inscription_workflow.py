"""Registration workflow: temporary password (72h) and admin validation status.

On ``utilisateur``: a temporary password that expires after 72 hours and a flag
forcing a password change at first login (banking-style).
On ``membre``: a registration status driving the admin validation flow, plus the
rejection reason and decision metadata. Existing members default to 'approuve'
so nothing they rely on changes.

Revision ID: 0013_inscription_workflow
Revises: 0012_document_storage
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0013_inscription_workflow"
down_revision = "0012_document_storage"
branch_labels = None
depends_on = None

STATUTS = ("incomplet", "soumis", "en_revue", "approuve", "refuse", "modification_demandee")


def upgrade() -> None:
    op.execute("ALTER TABLE utilisateur ADD COLUMN IF NOT EXISTS mdp_temporaire boolean NOT NULL DEFAULT false")
    op.execute("ALTER TABLE utilisateur ADD COLUMN IF NOT EXISTS mdp_expire_le timestamptz")
    op.execute("ALTER TABLE utilisateur ADD COLUMN IF NOT EXISTS doit_changer_mdp boolean NOT NULL DEFAULT false")

    statut_chk = ", ".join(f"'{v}'" for v in STATUTS)
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS statut_inscription text NOT NULL DEFAULT 'approuve'")
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS motif_refus text")
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS soumis_le timestamptz")
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS decision_le timestamptz")
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS decision_par uuid")
    op.execute(
        f"ALTER TABLE membre DROP CONSTRAINT IF EXISTS membre_statut_inscription_chk; "
        f"ALTER TABLE membre ADD CONSTRAINT membre_statut_inscription_chk "
        f"CHECK (statut_inscription IN ({statut_chk}))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE membre DROP CONSTRAINT IF EXISTS membre_statut_inscription_chk")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS statut_inscription")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS motif_refus")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS soumis_le")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS decision_le")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS decision_par")
    op.execute("ALTER TABLE utilisateur DROP COLUMN IF EXISTS mdp_temporaire")
    op.execute("ALTER TABLE utilisateur DROP COLUMN IF EXISTS mdp_expire_le")
    op.execute("ALTER TABLE utilisateur DROP COLUMN IF EXISTS doit_changer_mdp")
