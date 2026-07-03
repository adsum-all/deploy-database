"""Pending member data modifications awaiting final admin validation.

After the administration unlocks fields on a verified member, the member's edits
are not written straight to the member record. They are stored here as a pending
proposal (new values plus a snapshot of the previous values) until the
administration gives a final validation, like a bank or a public administration.
This keeps a full, auditable trail of every requested change.

Revision ID: 0016_modification_membre
Revises: 0015_org_publication
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0016_modification_membre"
down_revision = "0015_org_publication"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS modification_membre (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            membre_id uuid NOT NULL REFERENCES membre(id) ON DELETE CASCADE,
            demande_id uuid REFERENCES demande(id) ON DELETE SET NULL,
            valeurs jsonb NOT NULL,
            valeurs_avant jsonb NOT NULL DEFAULT '{}'::jsonb,
            statut text NOT NULL DEFAULT 'en_attente'
                CHECK (statut IN ('en_attente', 'validee', 'rejetee')),
            propose_le timestamptz NOT NULL DEFAULT now(),
            decide_le timestamptz,
            decide_par uuid
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_modification_membre_membre "
        "ON modification_membre (membre_id, statut)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_modification_membre_demande "
        "ON modification_membre (demande_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS modification_membre")
