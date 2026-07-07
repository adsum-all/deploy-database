# ruff: noqa: E501 - migrations carry long SQL and seeded text lines
"""Survey/attendance invitation notification for an activity, time-zone aware.

Seeds a ``sondage_activite`` notification type and its bilingual template. The
body carries ``{quand}`` (the activity start already localized to the recipient's
own time zone by the server) and ``{lien}`` (the lightweight check-in page), so a
member is invited to answer the attendance survey of a specific activity at the
right local time whatever their country.

Revision ID: 0073_sondage_activite
Revises: 0072_membre_fuseau_horaire
Create Date: 2026-07-05
"""
from __future__ import annotations

from alembic import op

revision = "0073_sondage_activite"
down_revision = "0072_membre_fuseau_horaire"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "INSERT INTO type_notification (cle, libelle, categorie, actif, scheduled, sensibilite) "
        "VALUES ('sondage_activite', 'Sondage de presence', 'activite', true, false, 'operationnel') "
        "ON CONFLICT (cle) DO UPDATE SET libelle = EXCLUDED.libelle, categorie = EXCLUDED.categorie"
    )
    op.execute(
        "INSERT INTO modele_message (cle, titre, corps, titre_en, corps_en, categorie) VALUES ("
        "'sondage_activite', "
        "'Sondage de presence : {titre}', "
        "'Bonjour {prenom}, l''activite « {titre} » commence {quand}. Merci de confirmer votre presence en quelques secondes : {lien}', "
        "'Attendance survey: {titre}', "
        "'Hello {prenom}, the activity « {titre} » starts {quand}. Please confirm your attendance in a few seconds: {lien}', "
        "'activite') ON CONFLICT (cle) DO UPDATE SET corps = EXCLUDED.corps, corps_en = EXCLUDED.corps_en, titre = EXCLUDED.titre, titre_en = EXCLUDED.titre_en"
    )


def downgrade() -> None:
    op.execute("DELETE FROM modele_message WHERE cle = 'sondage_activite'")
    op.execute("DELETE FROM type_notification WHERE cle = 'sondage_activite'")
