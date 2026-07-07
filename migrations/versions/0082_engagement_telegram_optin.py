# ruff: noqa: E501 - migrations carry long SQL lines
"""Discreet, non-forcing Telegram opt-in on the public engagement form.

A lead can optionally state they also wish to be reached on Telegram. The flag is
stored on the engagement invitation so the welcome team can follow up on that
channel. It is opt-in and defaults to false, so existing rows and people who do not
tick the box are never assumed to have consented.

Revision ID: 0082_engagement_telegram_optin
Revises: 0081_matricule_format_unique
Create Date: 2026-07-06
"""
from __future__ import annotations

from alembic import op

revision = "0082_engagement_telegram_optin"
down_revision = "0081_matricule_format_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE invitation_engagement ADD COLUMN IF NOT EXISTS souhaite_telegram boolean NOT NULL DEFAULT false")


def downgrade() -> None:
    op.execute("ALTER TABLE invitation_engagement DROP COLUMN IF EXISTS souhaite_telegram")
