# ruff: noqa: E501 - migrations carry long SQL lines
"""Automatic attendance-survey dispatch: a per-event sent marker and the admin settings.

Adds ``evenement.sondage_pointage_envoye_le`` so the frequent scheduler dispatches the
attendance survey of an activity exactly once (idempotent), and seeds the two settings
that make the automatic dispatch configurable by the administration:

* ``sondage_pointage_auto`` (bool, default true): master switch of the automatic survey.
* ``sondage_pointage_offset_min`` (int, default 0): minutes relative to the activity
  start when the survey fires (negative = before, 0 = at start, positive = after).

Revision ID: 0083_sondage_pointage_auto
Revises: 0082_engagement_telegram_optin
Create Date: 2026-07-06
"""
from __future__ import annotations

from alembic import op

revision = "0083_sondage_pointage_auto"
down_revision = "0082_engagement_telegram_optin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE evenement ADD COLUMN IF NOT EXISTS sondage_pointage_envoye_le timestamptz")
    op.execute(
        "INSERT INTO parametre (cle, valeur, categorie, description, maj_le) "
        "VALUES ('sondage_pointage_auto', 'true'::jsonb, 'sondage', 'Envoi automatique du sondage de pointage', now()) "
        "ON CONFLICT (cle) DO NOTHING"
    )
    op.execute(
        "INSERT INTO parametre (cle, valeur, categorie, description, maj_le) "
        "VALUES ('sondage_pointage_offset_min', '0'::jsonb, 'sondage', 'Minutes relatives au debut pour declencher le sondage (negatif=avant)', now()) "
        "ON CONFLICT (cle) DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DELETE FROM parametre WHERE cle IN ('sondage_pointage_auto', 'sondage_pointage_offset_min')")
    op.execute("ALTER TABLE evenement DROP COLUMN IF EXISTS sondage_pointage_envoye_le")
