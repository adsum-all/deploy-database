# ruff: noqa: E501 - migrations carry long SQL and seeded text lines
"""Unlock workflow deadlines, read receipts and notification lifecycle.

1. demande.echeance_reponse: deadline given to the member after an unlock or a
   correction request; the daily job closes overdue requests as 'sans suite'.
2. demande_message read receipts (lu_par_membre_le / lu_par_staff_le): both
   parties can see when the other side actually read a message.
3. notification.lu_le: individual, timestamped read marking (idempotent).
4. Central parameters: deblocage_delai_jours (SEEDED AT 30, THE LEAST
   DESTRUCTIVE VALUE; the business source mentions both 14 and 30 days, the
   arbitration is explicitly pending and the value is admin-editable, never
   hardcoded) and notification_retention_mois (6): interface notifications
   older than the retention are purged; conversation messages, requests,
   their history and the audit journal are NEVER touched by this purge.

Revision ID: 0053_deblocage_lecture
Revises: 0052_fenetre_modalite
Create Date: 2026-07-04
"""
from __future__ import annotations

from alembic import op

revision = "0053_deblocage_lecture"
down_revision = "0052_fenetre_modalite"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE demande ADD COLUMN IF NOT EXISTS echeance_reponse timestamptz")
    op.execute("ALTER TABLE demande_message ADD COLUMN IF NOT EXISTS lu_par_membre_le timestamptz")
    op.execute("ALTER TABLE demande_message ADD COLUMN IF NOT EXISTS lu_par_staff_le timestamptz")
    op.execute("ALTER TABLE notification ADD COLUMN IF NOT EXISTS lu_le timestamptz")
    op.execute("UPDATE notification SET lu_le = cree_le WHERE lu AND lu_le IS NULL")
    op.execute(
        "INSERT INTO parametre (cle, valeur, categorie, description) VALUES "
        "('deblocage_delai_jours', '30'::jsonb, 'demandes', "
        "'Delai de retour (jours) apres deblocage d''elements pour correction. ARBITRAGE METIER EN ATTENTE entre 14 et 30 jours : valeur par defaut 30 (la moins destructive), a ajuster ici une fois la regle tranchee.') "
        "ON CONFLICT (cle) DO NOTHING"
    )
    op.execute(
        "INSERT INTO parametre (cle, valeur, categorie, description) VALUES "
        "('notification_retention_mois', '6'::jsonb, 'notifications', "
        "'Duree de conservation (mois) des notifications d''interface. La purge ne touche JAMAIS les messages de conversation, les demandes, leur historique ni le journal d''audit.') "
        "ON CONFLICT (cle) DO NOTHING"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_notification_membre_date ON notification (membre_id, cree_le DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_demande_echeance ON demande (statut, echeance_reponse) WHERE echeance_reponse IS NOT NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE demande DROP COLUMN IF EXISTS echeance_reponse")
    op.execute("ALTER TABLE demande_message DROP COLUMN IF EXISTS lu_par_membre_le")
    op.execute("ALTER TABLE demande_message DROP COLUMN IF EXISTS lu_par_staff_le")
    op.execute("ALTER TABLE notification DROP COLUMN IF EXISTS lu_le")
    op.execute("DELETE FROM parametre WHERE cle IN ('deblocage_delai_jours', 'notification_retention_mois')")
    op.execute("DROP INDEX IF EXISTS idx_notification_membre_date")
    op.execute("DROP INDEX IF EXISTS idx_demande_echeance")
