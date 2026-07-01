"""Targeted registration corrections without restarting from scratch.

When the administration asks a member to correct their dossier, the member's
data stays in place (it already lives on the membre row) and only the targeted
fields are requested. champs_a_corriger marks those fields; correction_historique
keeps an old/new/who/when/why trail so the admin can review what changed.

Revision ID: 0031_correction
Revises: 0030_notif_workflow
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0031_correction"
down_revision = "0030_notif_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS champs_a_corriger text[]")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS correction_historique (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            membre_id uuid NOT NULL REFERENCES membre(id) ON DELETE CASCADE,
            champ text NOT NULL,
            ancienne_valeur text,
            nouvelle_valeur text,
            motif text,
            modifie_par uuid,
            modifie_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_correction_membre ON correction_historique (membre_id, modifie_le)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS correction_historique")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS champs_a_corriger")
