"""Training sessions: in-app session link, post-session questionnaire and
member notification preferences.

An event can carry a session link (Zoom, Meet, ...) the member joins from the
app. After the session, a questionnaire is available for a configurable window
(default six hours, stored in parametre). Members answer once; the administration
reads the responses. Members also choose which notifications they receive.

Revision ID: 0020_formation_questionnaire
Revises: 0019_photo_phash
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0020_formation_questionnaire"
down_revision = "0019_photo_phash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE evenement ADD COLUMN IF NOT EXISTS lien_session text")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS questionnaire (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            evenement_id uuid NOT NULL UNIQUE REFERENCES evenement(id) ON DELETE CASCADE,
            titre text NOT NULL DEFAULT 'Questionnaire de session',
            actif boolean NOT NULL DEFAULT true,
            cree_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS question (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            questionnaire_id uuid NOT NULL REFERENCES questionnaire(id) ON DELETE CASCADE,
            libelle text NOT NULL,
            type text NOT NULL DEFAULT 'texte' CHECK (type IN ('texte', 'choix', 'note')),
            options jsonb NOT NULL DEFAULT '[]'::jsonb,
            ordre integer NOT NULL DEFAULT 0
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_question_questionnaire ON question (questionnaire_id, ordre)")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS reponse_questionnaire (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            questionnaire_id uuid NOT NULL REFERENCES questionnaire(id) ON DELETE CASCADE,
            membre_id uuid NOT NULL REFERENCES membre(id) ON DELETE CASCADE,
            reponses jsonb NOT NULL,
            soumis_le timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT reponse_questionnaire_uq UNIQUE (questionnaire_id, membre_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS preference_notification (
            membre_id uuid PRIMARY KEY REFERENCES membre(id) ON DELETE CASCADE,
            evenements boolean NOT NULL DEFAULT true,
            demandes boolean NOT NULL DEFAULT true,
            rappels boolean NOT NULL DEFAULT true,
            email boolean NOT NULL DEFAULT true,
            maj_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        INSERT INTO parametre (cle, valeur, categorie, description)
        VALUES (
            'questionnaire_fenetre_heures', '6'::jsonb, 'formation',
            'Hours after a session ends during which its questionnaire stays open. Default 6h.'
        )
        ON CONFLICT (cle) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS reponse_questionnaire")
    op.execute("DROP TABLE IF EXISTS question")
    op.execute("DROP TABLE IF EXISTS questionnaire")
    op.execute("DROP TABLE IF EXISTS preference_notification")
    op.execute("ALTER TABLE evenement DROP COLUMN IF EXISTS lien_session")
    op.execute("DELETE FROM parametre WHERE cle = 'questionnaire_fenetre_heures'")
