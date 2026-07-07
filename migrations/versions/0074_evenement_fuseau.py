# ruff: noqa: E501 - migrations carry long SQL lines
"""Reference time zone of an activity, chosen at creation.

The start/end instants stay absolute (``timestamptz``); this column records the
zone the organizer entered them in (default ``Africa/Abidjan`` = GMT, the base's
home). It lets the front interpret the typed local time in the activity's own zone
before converting to UTC, so a France-based organizer scheduling a 12:00 activity
in Abidjan does not shift it by two hours, and every member still sees it in their
own local time.

Revision ID: 0074_evenement_fuseau
Revises: 0073_sondage_activite
Create Date: 2026-07-06
"""
from __future__ import annotations

from alembic import op

revision = "0074_evenement_fuseau"
down_revision = "0073_sondage_activite"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE evenement ADD COLUMN IF NOT EXISTS fuseau_horaire text NOT NULL DEFAULT 'Africa/Abidjan'")


def downgrade() -> None:
    op.execute("ALTER TABLE evenement DROP COLUMN IF EXISTS fuseau_horaire")
