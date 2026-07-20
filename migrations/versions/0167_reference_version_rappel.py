# ruff: noqa: E501 - migrations carry long SQL lines
"""Reference-date version history and the reminder notification type.

- ``date_reference_version``: an append-only JSONB snapshot of a reference date taken
  before every edit, so a previous version can be reviewed and restored.
- Seed the ``date_reference_rappel`` notification type and its bilingual message
  template, so the daily cron can remind members of an upcoming reference date when
  the admin set a reminder (reminders are off by default).

Revision ID: 0167_reference_version_rappel
Revises: 0166_calendrier_rls_maj_par
Create Date: 2026-07-20
"""
from __future__ import annotations

from alembic import op

revision = "0167_reference_version_rappel"
down_revision = "0166_calendrier_rls_maj_par"
branch_labels = None
depends_on = None

_LECTURE = "ARRAY['super_admin', 'admin', 'gestionnaire', 'direction']::text[]"
_ECRITURE = "ARRAY['super_admin', 'admin', 'gestionnaire']::text[]"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS date_reference_version (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            date_id uuid NOT NULL REFERENCES date_institutionnelle(id) ON DELETE CASCADE,
            snapshot jsonb NOT NULL,
            auteur_id uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            auteur_nom text,
            cree_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_date_reference_version ON date_reference_version(date_id, cree_le DESC)")
    op.execute("ALTER TABLE date_reference_version ENABLE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY date_reference_version_select ON date_reference_version FOR SELECT USING (adsum_current_role() = ANY({_LECTURE}))")
    op.execute(f"CREATE POLICY date_reference_version_write ON date_reference_version FOR ALL USING (adsum_current_role() = ANY({_ECRITURE})) WITH CHECK (adsum_current_role() = ANY({_ECRITURE}))")

    op.execute(
        "INSERT INTO type_notification (cle, libelle, categorie, scheduled) "
        "VALUES ('date_reference_rappel', 'Rappel d''une date de référence', 'rappel', true) "
        "ON CONFLICT (cle) DO NOTHING"
    )
    op.execute(
        "INSERT INTO modele_message (cle, titre, corps, titre_en, corps_en) VALUES ("
        "'date_reference_rappel', "
        "'Rappel : {titre_date}', "
        "'Bonjour {prenom}, la date « {titre_date} » approche ({jour}).', "
        "'Reminder: {titre_date}', "
        "'Hello {prenom}, the date \"{titre_date}\" is coming up ({jour}).'"
        ") ON CONFLICT (cle) DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DELETE FROM modele_message WHERE cle = 'date_reference_rappel'")
    op.execute("DELETE FROM type_notification WHERE cle = 'date_reference_rappel'")
    op.execute("DROP TABLE IF EXISTS date_reference_version")
