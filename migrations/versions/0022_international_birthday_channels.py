# ruff: noqa: E501 - migrations carry long SQL and seeded text lines
"""Internationalization, birthday module and notification channels.

- Members are worldwide: the phone dialling code is stored separately from the
  number (the number's country may differ from the residence country), and a
  general address (region + optional complement) is added.
- The birth year can be hidden: only the day and month (the birthday) are shown
  by default. A daily job wishes members a happy birthday.
- Notifications can be delivered over several channels (e-mail, in-app, Telegram,
  WhatsApp, SMS); recipient link ids and per-channel opt-ins are stored.

Revision ID: 0022_intl_birthday_channels
Revises: 0021_auth_attempt
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0022_intl_birthday_channels"
down_revision = "0021_auth_attempt"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Member: international phone, general address, birth-year visibility, channel ids.
    for col in (
        "indicatif_telephone text",
        "region text",
        "adresse_complement text",
        "naissance_annee_visible boolean NOT NULL DEFAULT false",
        "telegram_chat_id text",
        "telegram_link_token text",
        "whatsapp_numero text",
    ):
        op.execute(f"ALTER TABLE membre ADD COLUMN IF NOT EXISTS {col}")

    # Notification channel opt-ins (preference_notification already has evenements/demandes/rappels/email).
    for col in (
        "telegram boolean NOT NULL DEFAULT false",
        "whatsapp boolean NOT NULL DEFAULT false",
        "sms boolean NOT NULL DEFAULT false",
        "anniversaire boolean NOT NULL DEFAULT true",
    ):
        op.execute(f"ALTER TABLE preference_notification ADD COLUMN IF NOT EXISTS {col}")

    # Admin-editable message templates (birthday and future ones).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS modele_message (
            cle text PRIMARY KEY,
            titre text NOT NULL,
            corps text NOT NULL,
            image_url text,
            actif boolean NOT NULL DEFAULT true,
            maj_par uuid,
            maj_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        INSERT INTO modele_message (cle, titre, corps, image_url, actif)
        VALUES (
            'anniversaire',
            'Joyeux anniversaire {prenom} !',
            'Toute la fraternité vous souhaite un merveilleux anniversaire {prenom}. Que cette nouvelle annee soit remplie de grace, de paix et de joie. Nous rendons grace pour votre vie et votre engagement parmi nous.',
            NULL,
            true
        )
        ON CONFLICT (cle) DO NOTHING
        """
    )

    # One birthday send per member per year (idempotent daily cron).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_anniversaire (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            membre_id uuid NOT NULL REFERENCES membre(id) ON DELETE CASCADE,
            annee integer NOT NULL,
            canaux text NOT NULL DEFAULT '',
            cree_le timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT notification_anniversaire_uq UNIQUE (membre_id, annee)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS notification_anniversaire")
    op.execute("DROP TABLE IF EXISTS modele_message")
    for col in ("telegram", "whatsapp", "sms", "anniversaire"):
        op.execute(f"ALTER TABLE preference_notification DROP COLUMN IF EXISTS {col}")
    for col in ("indicatif_telephone", "region", "adresse_complement", "naissance_annee_visible", "telegram_chat_id", "telegram_link_token", "whatsapp_numero"):
        op.execute(f"ALTER TABLE membre DROP COLUMN IF EXISTS {col}")
