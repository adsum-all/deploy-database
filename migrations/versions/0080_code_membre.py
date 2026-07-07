# ruff: noqa: E501 - migrations carry long SQL lines
"""External member code (code_membre): an optional, member-specific identifier.

Distinct from the application matricule. It is the code a member carries in the wider
organisation (roughly two letters, then digits and letters, kept uppercase). Optional
(not everyone has one yet), can be filled later through a modification request, and
usable to identify a member at check-in alongside the matricule and phone+name.
Unique when present (case-insensitive), so it can serve as a lookup key.

Revision ID: 0080_code_membre
Revises: 0079_tracabilite_operateur
Create Date: 2026-07-06
"""
from __future__ import annotations

from alembic import op

revision = "0080_code_membre"
down_revision = "0079_tracabilite_operateur"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS code_membre text")
    # Unique only when present (partial, case-insensitive): a code identifies one
    # member, but the column stays optional.
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS membre_code_membre_uq ON membre (upper(code_membre)) WHERE code_membre IS NOT NULL")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS membre_code_membre_uq")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS code_membre")
