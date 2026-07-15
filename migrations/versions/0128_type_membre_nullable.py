# ruff: noqa: E501 - migrations carry long SQL lines
"""Make membre.type_membre (engagement level) nullable.

The engagement level (membre.type_membre) is a soft catalogue key, editable and
variable over time, and the API already treats it as optional (schemas expose it as
str | None, stats coalesce it to 'Non renseigne'). Only the column carried a legacy
NOT NULL, which broke the "retirer le niveau a tous puis supprimer" action: detaching
members from a level sets their type_membre to NULL, which the NOT NULL rejected.

Dropping the NOT NULL lets a member legitimately have no engagement level (pending a
new assignment), while the default 'membre_simple' still applies to inserts that omit
the column, so registration is unchanged.

Revision ID: 0128_type_membre_nullable
Revises: 0127_bot_observabilite
Create Date: 2026-07-12
"""
from __future__ import annotations

from alembic import op

revision = "0128_type_membre_nullable"
down_revision = "0127_bot_observabilite"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE membre ALTER COLUMN type_membre DROP NOT NULL")


def downgrade() -> None:
    # Re-imposing NOT NULL requires a value everywhere: backfill the default first.
    op.execute("UPDATE membre SET type_membre = 'membre_simple' WHERE type_membre IS NULL")
    op.execute("ALTER TABLE membre ALTER COLUMN type_membre SET NOT NULL")
