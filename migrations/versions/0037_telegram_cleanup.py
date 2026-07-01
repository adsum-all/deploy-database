"""Track outgoing Telegram messages so old ones can be auto-deleted.

Members' Telegram chats fill up with ADSUM notifications over time. Recording the
message ids the bot sends lets a scheduled job delete messages older than a
configurable retention window (default 90 days), keeping the chat tidy. A bot may
delete its own outgoing messages via the Telegram Bot API.

Revision ID: 0037_telegram_cleanup
Revises: 0036_notif_fr_accents
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0037_telegram_cleanup"
down_revision = "0036_notif_fr_accents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS telegram_message (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            chat_id text NOT NULL,
            message_id bigint NOT NULL,
            envoye_le timestamptz NOT NULL DEFAULT now(),
            supprime_le timestamptz
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_telegram_message_pending "
        "ON telegram_message (envoye_le) WHERE supprime_le IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS telegram_message")
