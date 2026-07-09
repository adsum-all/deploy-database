"""Live presence on collaboration cards (who is viewing a card right now).

A lightweight heartbeat table: one row per (viewer, card), refreshed while the card
is open. Viewers whose heartbeat is older than a short window are considered gone.
No websocket needed; the client polls. Rows are purged on card delete (CASCADE) and
naturally expire by timestamp.

Revision ID: 0107_collab_presence
Revises: 0106_item_assigne
"""
from __future__ import annotations

from alembic import op

revision = "0107_collab_presence"
down_revision = "0106_item_assigne"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collab_presence (
            carte_id uuid NOT NULL REFERENCES collab_carte(id) ON DELETE CASCADE,
            utilisateur_id uuid NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE,
            maj_le timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (carte_id, utilisateur_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_collab_presence_maj ON collab_presence (carte_id, maj_le)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS collab_presence")
