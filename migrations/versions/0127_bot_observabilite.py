# ruff: noqa: E501 - migrations carry long SQL lines
"""Observability of each workspace's instruction bot.

Records the last successful Telegram sync, the last ingested voice note and the
last failure (message + time) directly on collab_espace, so the back-office can
show a real, non-simulated health state per bot instead of a bare 'configured'
label. Columns only; nullable; no data change.

Revision ID: 0127_bot_observabilite
Revises: 0126_espace_bot_instruction
Create Date: 2026-07-12
"""
from __future__ import annotations

from alembic import op

revision = "0127_bot_observabilite"
down_revision = "0126_espace_bot_instruction"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE collab_espace ADD COLUMN IF NOT EXISTS instruction_derniere_synchro timestamptz")
    op.execute("ALTER TABLE collab_espace ADD COLUMN IF NOT EXISTS instruction_derniere_note timestamptz")
    op.execute("ALTER TABLE collab_espace ADD COLUMN IF NOT EXISTS instruction_dernier_echec text")
    op.execute("ALTER TABLE collab_espace ADD COLUMN IF NOT EXISTS instruction_dernier_echec_le timestamptz")


def downgrade() -> None:
    for col in ("instruction_dernier_echec_le", "instruction_dernier_echec",
                "instruction_derniere_note", "instruction_derniere_synchro"):
        op.execute(f"ALTER TABLE collab_espace DROP COLUMN IF EXISTS {col}")
