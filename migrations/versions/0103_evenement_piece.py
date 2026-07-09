"""Attachments (images and files) for an activity/event, edited identically from the
back office and the collaboration app. Files are stored inline as data URLs on the
row (same approach as the collaboration card attachments), size-capped by the API.

Revision ID: 0103_evenement_piece
Revises: 0102_evenement_desc_interv
"""
from __future__ import annotations

from alembic import op

revision = "0103_evenement_piece"
down_revision = "0102_evenement_desc_interv"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS evenement_piece (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            evenement_id uuid NOT NULL REFERENCES evenement(id) ON DELETE CASCADE,
            nom text NOT NULL,
            type text NOT NULL DEFAULT '',
            taille bigint NOT NULL DEFAULT 0,
            url text NOT NULL,
            cree_par uuid,
            cree_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_evenement_piece_evenement ON evenement_piece (evenement_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS evenement_piece")
