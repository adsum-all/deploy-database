# ruff: noqa: E501 - migrations carry long SQL lines
"""Make the tribu referential fully administrable like the other org referentials.

Adds a ``publie`` flag (controls visibility in the member registration dropdowns, exactly
like commission/coordination/intendance) so a tribe can be deactivated without deletion.
No data loss. The tribe list itself stays in the database, never hardcoded.

Revision ID: 0131_tribu_publie
Revises: 0130_membre_statut_archive
Create Date: 2026-07-13
"""
from __future__ import annotations

from alembic import op

revision = "0131_tribu_publie"
down_revision = "0130_membre_statut_archive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE tribu ADD COLUMN IF NOT EXISTS publie boolean NOT NULL DEFAULT true")


def downgrade() -> None:
    op.execute("ALTER TABLE tribu DROP COLUMN IF EXISTS publie")
