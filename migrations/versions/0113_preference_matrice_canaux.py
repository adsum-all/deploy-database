"""Per-group, per-channel notification matrix for members.

Members complained about e-mail volume. The existing preferences are all-or-nothing:
one master switch per channel and a per-category on/off that applies to every channel
at once. This adds a fine-grained matrix so a member can, per notification group,
choose e-mail on/off AND Telegram on/off independently (e.g. reminders on Telegram
but not by e-mail). Stored as JSONB, shape:

    {"rappels": {"email": true, "telegram": true}, "demarrage": {...}, ...}

Nullable: a NULL matrix keeps the previous behaviour (backward compatible), and any
group absent from the matrix falls back to the default (both channels on). Critical
messages (OTP, security) and the mandatory attendance survey ignore the matrix.

Additive only. Revision ID: 0113_preference_matrice_canaux
Revises: 0112_telegram_message_contexte
"""
from __future__ import annotations

from alembic import op

revision = "0113_preference_matrice_canaux"
down_revision = "0112_telegram_message_contexte"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE preference_notification ADD COLUMN IF NOT EXISTS matrice_canaux jsonb")


def downgrade() -> None:
    op.execute("ALTER TABLE preference_notification DROP COLUMN IF EXISTS matrice_canaux")
