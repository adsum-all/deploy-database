# ruff: noqa: E501 - migrations carry long SQL lines
"""Configurable first day of the week for the weekly recap/agenda notifications.

Different organisations start their week on different days (Monday, Saturday...). The weekly
recap (previous week) and agenda (current week) derive their bounds from this parameter, so
the platform is not tied to one organisation's calendar. 0 = Monday ... 6 = Sunday. Default
Monday, matching Sacerdoce Royal (week = Monday..Sunday inclusive).

Revision ID: 0141_semaine_jour_debut
Revises: 0140_notif_recipient_security
Create Date: 2026-07-13
"""
from __future__ import annotations

from alembic import op

revision = "0141_semaine_jour_debut"
down_revision = "0140_notif_recipient_security"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("INSERT INTO parametre (cle, valeur) VALUES ('semaine_jour_debut', '0'::jsonb) ON CONFLICT (cle) DO NOTHING")


def downgrade() -> None:
    op.execute("DELETE FROM parametre WHERE cle = 'semaine_jour_debut'")
