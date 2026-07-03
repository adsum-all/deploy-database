"""Global per-channel On/Off switch for notifications.

An administrator can disable a whole delivery channel (e-mail, Telegram,
WhatsApp, SMS) without touching its credentials: a kill-switch on top of the
configuration and the per-member preferences. In-app is always on. Default: on.

Revision ID: 0043_canal_switch
Revises: 0042_rls_hardening
Create Date: 2026-07-02
"""
from __future__ import annotations

from alembic import op

revision = "0043_canal_switch"
down_revision = "0042_rls_hardening"
branch_labels = None
depends_on = None

_KEYS = ["canal_email", "canal_telegram", "canal_whatsapp", "canal_sms"]


def upgrade() -> None:
    for cle in _KEYS:
        op.execute(
            "INSERT INTO integration_config (cle, valeur, categorie) VALUES (%s, 'on', 'canaux') "
            "ON CONFLICT (cle) DO NOTHING",
            (cle,),
        )


def downgrade() -> None:
    for cle in _KEYS:
        op.execute("DELETE FROM integration_config WHERE cle = %s", (cle,))
