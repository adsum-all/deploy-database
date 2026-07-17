# ruff: noqa: E501 - migrations carry long SQL lines
"""Make notification recipients strictly personal: no shared/ambiguous Telegram chat.

Root causes fixed (audit 2026-07-13):
- ``membre.telegram_chat_id`` had NO uniqueness, so two members could share one Telegram
  chat (shared phone, a leader linking several members from their own Telegram). A member's
  login OTP then reached another person. A partial UNIQUE index makes a chat exclusive to a
  single member.
- E-mail resolution used lower(email) while the UNIQUE was case-sensitive, so two accounts
  differing only by letter case could both exist and a login could resolve to the wrong one.
  Case-insensitive UNIQUE indexes remove any such tie.
- Telegram linking trusted mere possession of the deep-link token. New columns support a
  proof-of-possession step: the bot sends a one-time code TO the candidate chat and the
  member must re-enter it in the app to confirm they control that chat.

Revision ID: 0140_notif_recipient_security
Revises: 0139_app_mobile_non_doublon
Create Date: 2026-07-13
"""
from __future__ import annotations

from alembic import op

revision = "0140_notif_recipient_security"
down_revision = "0139_app_mobile_non_doublon"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) A Telegram chat belongs to exactly one member.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_membre_telegram_chat_id "
        "ON membre (telegram_chat_id) WHERE telegram_chat_id IS NOT NULL"
    )
    # 2) Case-insensitive account identity (no two accounts differing only by e-mail case).
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_utilisateur_email_lower "
        "ON utilisateur (lower(email)) WHERE email IS NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_membre_email_lower "
        "ON membre (lower(email)) WHERE email IS NOT NULL AND email <> ''"
    )
    # 3) Proof-of-possession columns for the secure Telegram linking flow.
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS telegram_pending_chat_id text")
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS telegram_confirm_code text")
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS telegram_confirm_expire timestamptz")
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS telegram_confirm_essais smallint NOT NULL DEFAULT 0")


def downgrade() -> None:
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS telegram_confirm_essais")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS telegram_confirm_expire")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS telegram_confirm_code")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS telegram_pending_chat_id")
    op.execute("DROP INDEX IF EXISTS ux_membre_email_lower")
    op.execute("DROP INDEX IF EXISTS ux_utilisateur_email_lower")
    op.execute("DROP INDEX IF EXISTS ux_membre_telegram_chat_id")
