# ruff: noqa: E501 - migrations carry long SQL lines
"""Activity cancellation: cancel an activity without deleting it.

A programmed activity may need to be called off (change of plan) while keeping its
history. ``annule`` marks it cancelled, ``annule_le`` / ``annule_motif`` record when
and why. A cancelled activity no longer triggers the automatic attendance survey and
is shown as cancelled in the admin calendar; deletion stays reserved for activities
with no attendance yet.

Revision ID: 0084_evenement_annulation
Revises: 0083_sondage_pointage_auto
Create Date: 2026-07-06
"""
from __future__ import annotations

from alembic import op

revision = "0084_evenement_annulation"
down_revision = "0083_sondage_pointage_auto"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE evenement ADD COLUMN IF NOT EXISTS annule boolean NOT NULL DEFAULT false")
    op.execute("ALTER TABLE evenement ADD COLUMN IF NOT EXISTS annule_le timestamptz")
    op.execute("ALTER TABLE evenement ADD COLUMN IF NOT EXISTS annule_motif text")


def downgrade() -> None:
    op.execute("ALTER TABLE evenement DROP COLUMN IF EXISTS annule_motif")
    op.execute("ALTER TABLE evenement DROP COLUMN IF EXISTS annule_le")
    op.execute("ALTER TABLE evenement DROP COLUMN IF EXISTS annule")
