"""Add per-unit birthday overlay preferences to the member calendar.

Members already toggle VIP / responsables / own-commission birthdays. This adds
three more own-unit overlay categories so a member can also surface the birthdays
of their tribe, their coordination and their intendance in the calendar. All off
by default so nothing changes for existing members until they opt in.

Revision ID: 0087_cal_categories_unite
Revises: 0086_repair_verifies_en_attente
"""
from __future__ import annotations

from alembic import op

revision = "0087_cal_categories_unite"
down_revision = "0086_repair_verifies_en_attente"
branch_labels = None
depends_on = None

_COLS = ("cal_tribu", "cal_coordination", "cal_intendance")


def upgrade() -> None:
    for col in _COLS:
        op.execute(f"ALTER TABLE preference_notification ADD COLUMN IF NOT EXISTS {col} boolean NOT NULL DEFAULT false")


def downgrade() -> None:
    for col in _COLS:
        op.execute(f"ALTER TABLE preference_notification DROP COLUMN IF EXISTS {col}")
