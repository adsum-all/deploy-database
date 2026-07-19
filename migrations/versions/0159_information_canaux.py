# ruff: noqa: E501 - migrations carry long SQL lines
"""Diffusion channels on an Information.

``canaux`` stores which channels an Information is broadcast on when published
(the in-app feed is always included). Default: in-app plus Telegram, so a
configured Telegram relay carries institutional communications by default.

Revision ID: 0159_information_canaux
Revises: 0158_retention_archivage
Create Date: 2026-07-19
"""
from __future__ import annotations

from alembic import op

revision = "0159_information_canaux"
down_revision = "0158_retention_archivage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE information ADD COLUMN IF NOT EXISTS canaux jsonb NOT NULL DEFAULT '[\"application\", \"telegram\"]'::jsonb")


def downgrade() -> None:
    op.execute("ALTER TABLE information DROP COLUMN IF EXISTS canaux")
