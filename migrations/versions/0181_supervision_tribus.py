# ruff: noqa: E501 - migrations carry long SQL lines
"""Record who supervises which tribe, and keep the history of it.

A tribe has a patriarche, and the patriarche must belong to the tribe. Supervision is
a different relation: whoever answers for a tribe before the governance is often not
one of its members, and one person can answer for several tribes. Nothing recorded
that, so the question "who supervises this tribe, since when, appointed by whom" had
no answer anywhere in the platform.

The shape mirrors tribu_patriarche_historique, which already answers the same question
for the patriarche function: a current row plus a closed history, rather than an
overwrite that erases who held the responsibility last month.

A supervision can be carried by a person or by a special team, because both happen:
a tribe answers to an individual, or to a standing body. Exactly one of the two is
required, which the check constraint enforces rather than trusting the callers.

Revision ID: 0181_supervision_tribus
Revises: 0180_permission_par_application
Create Date: 2026-07-29
"""
from __future__ import annotations

from alembic import op

revision = "0181_supervision_tribus"
down_revision = "0180_permission_par_application"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tribu_supervision (
            id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tribu_id            uuid NOT NULL REFERENCES tribu(id) ON DELETE CASCADE,
            -- Exactly one of the two carries the responsibility.
            membre_id           uuid REFERENCES membre(id) ON DELETE CASCADE,
            equipe_speciale_id  uuid REFERENCES equipe_speciale(id) ON DELETE CASCADE,
            role_supervision    text NOT NULL DEFAULT 'superviseur',
            debut               timestamptz NOT NULL DEFAULT now(),
            fin                 timestamptz,
            attribue_par        uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            motif               text,
            cree_le             timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT tribu_supervision_porteur_unique CHECK (
                (membre_id IS NOT NULL AND equipe_speciale_id IS NULL)
                OR (membre_id IS NULL AND equipe_speciale_id IS NOT NULL)
            ),
            CONSTRAINT tribu_supervision_periode CHECK (fin IS NULL OR fin >= debut)
        )
        """
    )
    # One open supervision per tribe and per holder: appointing the same person twice
    # without closing the first would make "who supervises this tribe" ambiguous, and
    # the answer to that question is the whole point of the table.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS tribu_supervision_ouverte_membre_uniq "
        "ON tribu_supervision (tribu_id, membre_id) WHERE fin IS NULL AND membre_id IS NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS tribu_supervision_ouverte_equipe_uniq "
        "ON tribu_supervision (tribu_id, equipe_speciale_id) WHERE fin IS NULL AND equipe_speciale_id IS NOT NULL"
    )
    op.execute("CREATE INDEX IF NOT EXISTS tribu_supervision_tribu_idx ON tribu_supervision (tribu_id) WHERE fin IS NULL")
    op.execute("CREATE INDEX IF NOT EXISTS tribu_supervision_membre_idx ON tribu_supervision (membre_id) WHERE fin IS NULL")
    op.execute("ALTER TABLE tribu_supervision ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON tribu_supervision FROM anon, authenticated")

    # Membership of a special team was a hard row that a removal deleted outright, so
    # who sat on a body last year was unanswerable. These columns turn the removal
    # into a closed period, the same way every other responsibility is recorded here.
    op.execute("ALTER TABLE membre_equipe_speciale ADD COLUMN IF NOT EXISTS debut timestamptz NOT NULL DEFAULT now()")
    op.execute("ALTER TABLE membre_equipe_speciale ADD COLUMN IF NOT EXISTS fin timestamptz")
    op.execute("ALTER TABLE membre_equipe_speciale ADD COLUMN IF NOT EXISTS attribue_par uuid")
    op.execute("ALTER TABLE membre_equipe_speciale ADD COLUMN IF NOT EXISTS motif text")
    op.execute(
        "ALTER TABLE membre_equipe_speciale DROP CONSTRAINT IF EXISTS mes_attribue_par_fk"
    )
    op.execute(
        "ALTER TABLE membre_equipe_speciale ADD CONSTRAINT mes_attribue_par_fk "
        "FOREIGN KEY (attribue_par) REFERENCES utilisateur(id) ON DELETE SET NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS membre_equipe_speciale_ouverte_idx "
        "ON membre_equipe_speciale (equipe_id) WHERE fin IS NULL"
    )

    # The registration form asks whether the member belongs to the leading team. The
    # answer was written and read back, and nothing ever turned it into a membership:
    # a declaration nobody could act on. This is the queue that makes it actionable.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS declaration_equipe_dirigeante (
            id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            membre_id     uuid NOT NULL REFERENCES membre(id) ON DELETE CASCADE,
            declaree_le   timestamptz NOT NULL DEFAULT now(),
            statut        text NOT NULL DEFAULT 'a_traiter',
            traitee_le    timestamptz,
            traitee_par   uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            commentaire   text,
            CONSTRAINT declaration_equipe_dirigeante_statut CHECK (
                statut IN ('a_traiter', 'confirmee', 'refusee')
            )
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS declaration_equipe_dirigeante_ouverte_uniq "
        "ON declaration_equipe_dirigeante (membre_id) WHERE statut = 'a_traiter'"
    )
    op.execute("ALTER TABLE declaration_equipe_dirigeante ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON declaration_equipe_dirigeante FROM anon, authenticated")

    # Import the declarations already made, so the queue does not start empty while
    # members are waiting on an answer they gave weeks ago.
    op.execute(
        """
        INSERT INTO declaration_equipe_dirigeante (membre_id, declaree_le, statut)
        SELECT m.id, COALESCE(m.cree_le, now()), 'a_traiter'
          FROM membre m
         WHERE COALESCE(m.equipe_dirigeante_declaree, false) = true
           AND NOT EXISTS (
               SELECT 1 FROM declaration_equipe_dirigeante d WHERE d.membre_id = m.id
           )
        """
    )

    # The permission that guards the supervision screens, alongside the existing
    # organisation.equipes. Declared here so the catalogue and the base agree.
    op.execute(
        """
        INSERT INTO permission (cle, domaine, libelle, description, risque, portee, systeme)
        VALUES ('organisation.supervision', 'tribus', 'Tribus - supervision',
                'Désigner qui supervise une tribu, clore une supervision et consulter son historique.',
                'eleve', 'global', false)
        ON CONFLICT (cle) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO permission_application (permission, application_code)
        SELECT 'organisation.supervision', a.code
          FROM application a
         WHERE a.code IN ('back-office', 'pilotage', 'direction')
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM permission_application WHERE permission = 'organisation.supervision'")
    op.execute("DELETE FROM permission WHERE cle = 'organisation.supervision'")
    op.execute("DROP TABLE IF EXISTS declaration_equipe_dirigeante")
    op.execute("DROP TABLE IF EXISTS tribu_supervision")
    op.execute("ALTER TABLE membre_equipe_speciale DROP COLUMN IF EXISTS motif")
    op.execute("ALTER TABLE membre_equipe_speciale DROP COLUMN IF EXISTS attribue_par")
    op.execute("ALTER TABLE membre_equipe_speciale DROP COLUMN IF EXISTS fin")
    op.execute("ALTER TABLE membre_equipe_speciale DROP COLUMN IF EXISTS debut")
