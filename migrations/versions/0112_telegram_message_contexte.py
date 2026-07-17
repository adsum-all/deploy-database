"""Tag tracked Telegram messages with a context so a class of message can be
deleted precisely.

A one-time login code delivered over Telegram must be removed from the chat once it
has been used (or superseded), so the secret does not linger in the member's chat.
The context column labels those messages (e.g. ``otp:login_2fa``) so the deletion
targets only them, leaving ordinary notifications untouched. Nullable: existing rows
and plain notifications keep a NULL context.

Additive only. Revision ID: 0112_telegram_message_contexte
Revises: 0111_canal_audio_retention
"""
from __future__ import annotations

from alembic import op

revision = "0112_telegram_message_contexte"
down_revision = "0111_canal_audio_retention"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE telegram_message ADD COLUMN IF NOT EXISTS contexte text")
    # Fast lookup of the live tracked messages for a chat and context on deletion.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_telegram_message_chat_contexte "
        "ON telegram_message (chat_id, contexte) WHERE supprime_le IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_telegram_message_chat_contexte")
    op.execute("ALTER TABLE telegram_message DROP COLUMN IF EXISTS contexte")
