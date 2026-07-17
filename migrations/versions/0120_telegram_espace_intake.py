# ruff: noqa: E501 - migrations carry long SQL lines
"""Per-general-workspace Telegram intake and voice-note routing.

Telegram does not allow creating a bot per workspace (BotFather is manual, no
API), so each general workspace instead gets its own intake token, generated
automatically at creation (never for a sub-space). A linked member opens the
workspace deep link (t.me/<bot>?start=canal_<token>) once; this binds their chat
to that workspace (membre.telegram_espace_id). Their voice notes then route to
that workspace's channel instead of the global one, so each department gets its
own instruction channel.

Revision ID: 0120_telegram_espace_intake
Revises: 0119_telegram_voice_ingest
Create Date: 2026-07-11
"""
from __future__ import annotations

from alembic import op

revision = "0120_telegram_espace_intake"
down_revision = "0119_telegram_voice_ingest"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Per-workspace intake token (general workspaces only; a sub-space keeps NULL).
    op.execute("ALTER TABLE collab_espace ADD COLUMN IF NOT EXISTS telegram_intake_token text")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_collab_espace_intake_token "
        "ON collab_espace (telegram_intake_token) WHERE telegram_intake_token IS NOT NULL"
    )
    # The workspace a member's Telegram voice notes route to (set when they open a
    # workspace's deep link). SET NULL if that workspace is deleted.
    op.execute(
        "ALTER TABLE membre ADD COLUMN IF NOT EXISTS telegram_espace_id uuid "
        "REFERENCES collab_espace(id) ON DELETE SET NULL"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS telegram_espace_id")
    op.execute("DROP INDEX IF EXISTS ux_collab_espace_intake_token")
    op.execute("ALTER TABLE collab_espace DROP COLUMN IF EXISTS telegram_intake_token")
