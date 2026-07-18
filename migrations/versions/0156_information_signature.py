# ruff: noqa: E501 - migrations carry long SQL lines
"""Optional signature block on an Information.

``signature`` (free text: the moderator, the founder, the administration, a
specific person) and ``signature_url`` (typically the official site) render as a
distinct closing block in the member app.

Revision ID: 0156_information_signature
Revises: 0155_tts_cache
Create Date: 2026-07-18
"""
from __future__ import annotations

from alembic import op

revision = "0156_information_signature"
down_revision = "0155_tts_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE information ADD COLUMN IF NOT EXISTS signature text")
    op.execute("ALTER TABLE information ADD COLUMN IF NOT EXISTS signature_url text")


def downgrade() -> None:
    op.execute("ALTER TABLE information DROP COLUMN IF EXISTS signature_url")
    op.execute("ALTER TABLE information DROP COLUMN IF EXISTS signature")
