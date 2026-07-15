# ruff: noqa: E501 - migrations carry long SQL lines
"""Reset every Telegram link so all members re-link through the secure proof-of-possession flow.

The previous linking could bind a chat without proving the member controls it, and a bug made
confirmation fail. To guarantee a clean, verified state for everyone (existing and new), we
clear every stored Telegram chat and any pending link; each member re-links themselves via the
new flow (request link, press Start, enter the code the bot sends to their chat). The Telegram
channel preference is kept: once re-linked, delivery resumes automatically.

Revision ID: 0142_telegram_relink_all
Revises: 0141_semaine_jour_debut
Create Date: 2026-07-13
"""
from __future__ import annotations

from alembic import op

revision = "0142_telegram_relink_all"
down_revision = "0141_semaine_jour_debut"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE membre SET telegram_chat_id = NULL, telegram_pending_chat_id = NULL, "
        "telegram_confirm_code = NULL, telegram_confirm_expire = NULL, telegram_confirm_essais = 0, "
        "telegram_link_token = NULL "
        "WHERE telegram_chat_id IS NOT NULL OR telegram_pending_chat_id IS NOT NULL OR telegram_link_token IS NOT NULL"
    )


def downgrade() -> None:
    # A security reset cannot be undone: the previous, unverified chat links are intentionally gone.
    pass
