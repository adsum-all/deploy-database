"""Add the missing account foreign key on collab_item_assigne.

0106 created collab_item_assigne with utilisateur_id as a bare uuid (no FK), so a
deleted account left dangling assignment rows that the item read then surfaced as a
ghost assignee. This mirrors the defensive pattern of 0099: purge any rows already
orphaned, then add REFERENCES utilisateur(id) ON DELETE CASCADE (CASCADE, not SET
NULL, because utilisateur_id is part of the composite primary key).

Revision ID: 0108_item_assigne_fk
Revises: 0107_collab_presence
"""
from __future__ import annotations

from alembic import op

revision = "0108_item_assigne_fk"
down_revision = "0107_collab_presence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM collab_item_assigne WHERE utilisateur_id NOT IN (SELECT id FROM utilisateur)")
    op.execute(
        "ALTER TABLE collab_item_assigne ADD CONSTRAINT fk_collab_item_assigne_utilisateur "
        "FOREIGN KEY (utilisateur_id) REFERENCES utilisateur(id) ON DELETE CASCADE"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE collab_item_assigne DROP CONSTRAINT IF EXISTS fk_collab_item_assigne_utilisateur")
