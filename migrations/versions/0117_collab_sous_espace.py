# ruff: noqa: E501 - migrations carry long SQL lines
"""Sub-spaces: a collaboration space can belong to a parent space.

Adds a self-referential ``parent_id`` to ``collab_espace`` so the collaboration
app gains a GitLab-style hierarchy: a top-level workspace (parent_id NULL) groups
sub-spaces, and boards live under either level. Kept to a single self-reference
(no separate table) so all existing space machinery (membership, roles, boards,
labels, RLS) applies unchanged to a sub-space. Depth is capped to one level by the
API (a sub-space cannot itself have sub-spaces). ON DELETE SET NULL so removing a
parent never silently destroys a sub-space and its data (it becomes top-level).

Revision ID: 0117_collab_sous_espace
Revises: 0116_rls_niveau_canal
Create Date: 2026-07-11
"""
from __future__ import annotations

from alembic import op

revision = "0117_collab_sous_espace"
down_revision = "0116_rls_niveau_canal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE collab_espace ADD COLUMN IF NOT EXISTS parent_id uuid REFERENCES collab_espace(id) ON DELETE SET NULL")
    op.execute("CREATE INDEX IF NOT EXISTS collab_espace_parent_idx ON collab_espace (parent_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS collab_espace_parent_idx")
    op.execute("ALTER TABLE collab_espace DROP COLUMN IF EXISTS parent_id")
