"""Publication flag on organizational lists.

The admin can create an organizational entry (coordination, intendance,
commission, group) without publishing it. Only published entries appear in the
member-facing registration dropdowns. Existing entries default to published so
nothing currently visible disappears.

Revision ID: 0015_org_publication
Revises: 0014_role_membre
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0015_org_publication"
down_revision = "0014_role_membre"
branch_labels = None
depends_on = None

TABLES = ("commission", "intendance", "coordination", "sous_commission")


def upgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS publie boolean NOT NULL DEFAULT true")


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS publie")
