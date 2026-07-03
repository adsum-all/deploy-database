"""Notification catalogue, bilingual templates, member language and send log.

Members receive a full range of notifications (transactional, activity reminders,
weekly agenda/recap, community) over their chosen channels (in-app, e-mail,
Telegram by default; WhatsApp/SMS when configured). Each type can be disabled by
the administration; each has a French and an English template; the member's
language decides which is sent. A send log deduplicates scheduled sends so a
member is never spammed.

Revision ID: 0024_notifications
Revises: 0023_participation
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0024_notifications"
down_revision = "0023_participation"
branch_labels = None
depends_on = None

# (cle, libelle, categorie, scheduled)
_TYPES = [
    ("compte_cree", "Compte cree", "transactionnel", False),
    ("inscription_decision", "Decision d'inscription", "transactionnel", False),
    ("demande_reponse", "Reponse a une demande", "transactionnel", False),
    ("modification_decision", "Decision de modification", "transactionnel", False),
    ("document_demande", "Document demande", "transactionnel", False),
    ("otp", "Code de verification", "transactionnel", False),
    ("activite_rappel_j1", "Rappel J-1 d'une activite", "activite", True),
    ("activite_rappel_start", "Rappel au demarrage", "activite", True),
    ("activite_demarree", "Activite demarree", "activite", True),
    ("agenda_hebdo", "Agenda de la semaine", "activite", True),
    ("recap_hebdo", "Recapitulatif de la semaine", "activite", True),
    ("activite_modifiee", "Activite modifiee", "activite", False),
    ("questionnaire_disponible", "Questionnaire disponible", "activite", False),
    ("anniversaire", "Souhaits d'anniversaire", "communaute", True),
    ("annonce", "Annonce de l'administration", "communaute", False),
]


def upgrade() -> None:
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS langue text NOT NULL DEFAULT 'fr'")
    op.execute("ALTER TABLE membre DROP CONSTRAINT IF EXISTS membre_langue_chk")
    op.execute("ALTER TABLE membre ADD CONSTRAINT membre_langue_chk CHECK (langue IN ('fr', 'en'))")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS type_notification (
            cle text PRIMARY KEY,
            libelle text NOT NULL,
            categorie text NOT NULL,
            actif boolean NOT NULL DEFAULT true,
            scheduled boolean NOT NULL DEFAULT false,
            maj_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    for cle, libelle, categorie, scheduled in _TYPES:
        op.execute(
            "INSERT INTO type_notification (cle, libelle, categorie, scheduled) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (cle) DO NOTHING",
            (cle, libelle, categorie, scheduled),
        )

    # Bilingual templates live in modele_message (birthday already there).
    op.execute("ALTER TABLE modele_message ADD COLUMN IF NOT EXISTS titre_en text")
    op.execute("ALTER TABLE modele_message ADD COLUMN IF NOT EXISTS corps_en text")
    op.execute("ALTER TABLE modele_message ADD COLUMN IF NOT EXISTS categorie text")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_log (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            membre_id uuid NOT NULL REFERENCES membre(id) ON DELETE CASCADE,
            type_cle text NOT NULL,
            ref_id text NOT NULL DEFAULT '',
            canaux text NOT NULL DEFAULT '',
            cree_le timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT notification_log_uq UNIQUE (membre_id, type_cle, ref_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_notification_log_type ON notification_log (type_cle, cree_le)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS notification_log")
    op.execute("DROP TABLE IF EXISTS type_notification")
    op.execute("ALTER TABLE membre DROP CONSTRAINT IF EXISTS membre_langue_chk")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS langue")
    op.execute("ALTER TABLE modele_message DROP COLUMN IF EXISTS titre_en")
    op.execute("ALTER TABLE modele_message DROP COLUMN IF EXISTS corps_en")
