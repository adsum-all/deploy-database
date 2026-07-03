"""Admin-configurable integration settings (channel tokens).

Keys such as the Telegram bot token can be viewed (masked) and rotated from the
administration interface, so a compromised token can be replaced immediately
without a redeployment. The application reads the live value here first and falls
back to the environment. Values are secret; only admins may read or change them,
and every change is audited.

Revision ID: 0025_integration_config
Revises: 0024_notifications
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0025_integration_config"
down_revision = "0024_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS integration_config (
            cle text PRIMARY KEY,
            valeur text,
            categorie text NOT NULL DEFAULT 'general',
            maj_par uuid,
            maj_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    # Seed the known channel keys (empty rows appear in the admin UI to be filled).
    for cle, categorie in (
        ("telegram_bot_token", "telegram"),
        ("telegram_bot_username", "telegram"),
    ):
        op.execute(
            "INSERT INTO integration_config (cle, categorie) VALUES (%s, %s) ON CONFLICT (cle) DO NOTHING",
            (cle, categorie),
        )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS integration_config")
