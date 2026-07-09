"""Multiple assignees per checklist item.

A checklist item could carry a single assignee (collab_checklist_item.assigne_id).
This adds a join table so several people can be assigned to one item, and backfills
the existing single assignees. The old column is kept (first assignee) for backward
compatibility.

Revision ID: 0106_item_assigne
Revises: 0105_collab_piece_storage
"""
from __future__ import annotations

from alembic import op

revision = "0106_item_assigne"
down_revision = "0105_collab_piece_storage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collab_item_assigne (
            item_id uuid NOT NULL REFERENCES collab_checklist_item(id) ON DELETE CASCADE,
            utilisateur_id uuid NOT NULL,
            PRIMARY KEY (item_id, utilisateur_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_collab_item_assigne_item ON collab_item_assigne (item_id)")
    op.execute(
        "INSERT INTO collab_item_assigne (item_id, utilisateur_id) "
        "SELECT id, assigne_id FROM collab_checklist_item WHERE assigne_id IS NOT NULL "
        "ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS collab_item_assigne")
