# ruff: noqa: E501 - migrations carry long SQL lines
"""Special teams (equipes speciales) and their membership.

Some members belong to official cross-cutting teams that are NOT part of the
geographic/functional hierarchy (commission, intendance, tribu): the leadership
team, the shepherds' college, the founder's assistants group, and others that may
appear over time. Three pieces:

- ``organisation.equipes``: a permission that gates the special-teams management
  page. Held by super_admin and admin by default, delegable to any member through a
  governance group, so only that role sees the page.
- ``equipe_speciale``: the team itself (name, optional stable code for the well-known
  ones, description, official flag, active flag, display order).
- ``membre_equipe_speciale``: the membership (a member belongs to zero or more teams,
  with a role in each). Deleting a team or a member cascades the membership rows.

A lightweight self-declaration column ``equipe_dirigeante_declaree`` is added on
``membre`` so a person can declare at registration that they are part of the
leadership team; an administrator confirms it by adding a real membership row (the
declaration alone never grants anything), mirroring the berger declaration flow.

Revision ID: 0168_equipes_speciales
Revises: 0167_reference_version_rappel
Create Date: 2026-07-21
"""
from __future__ import annotations

from alembic import op

revision = "0168_equipes_speciales"
down_revision = "0167_reference_version_rappel"
branch_labels = None
depends_on = None

_COMITE = "ARRAY['super_admin', 'admin', 'gestionnaire']::text[]"
_LECTURE = "ARRAY['super_admin', 'admin', 'gestionnaire', 'direction']::text[]"


def upgrade() -> None:
    # Permission (must exist before any governance group can reference it).
    op.execute(
        "INSERT INTO permission (cle, domaine, libelle, risque, portee, systeme) "
        "VALUES ('organisation.equipes', 'organisation', 'Organisation - équipes spéciales', 'moyen', 'global', true) "
        "ON CONFLICT (cle) DO NOTHING"
    )
    op.execute(
        "INSERT INTO role_permission (role, permission) "
        "SELECT r, 'organisation.equipes' FROM (VALUES ('super_admin'), ('admin')) AS v(r) "
        "ON CONFLICT DO NOTHING"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS equipe_speciale (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            code text UNIQUE,
            nom text NOT NULL,
            description text NOT NULL DEFAULT '',
            officielle boolean NOT NULL DEFAULT true,
            active boolean NOT NULL DEFAULT true,
            ordre integer NOT NULL DEFAULT 0,
            cree_le timestamptz NOT NULL DEFAULT now(),
            maj_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_equipe_speciale_nom ON equipe_speciale(lower(nom))")
    op.execute("ALTER TABLE equipe_speciale ENABLE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY equipe_speciale_select ON equipe_speciale FOR SELECT USING (adsum_current_role() = ANY({_LECTURE}))")
    op.execute(f"CREATE POLICY equipe_speciale_write ON equipe_speciale FOR ALL USING (adsum_current_role() = ANY({_COMITE})) WITH CHECK (adsum_current_role() = ANY({_COMITE}))")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS membre_equipe_speciale (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            equipe_id uuid NOT NULL REFERENCES equipe_speciale(id) ON DELETE CASCADE,
            membre_id uuid NOT NULL REFERENCES membre(id) ON DELETE CASCADE,
            role text NOT NULL DEFAULT 'membre',
            actif boolean NOT NULL DEFAULT true,
            cree_le timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT membre_equipe_speciale_uni UNIQUE (equipe_id, membre_id),
            CONSTRAINT membre_equipe_speciale_role_chk CHECK (role IN ('membre', 'responsable'))
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_membre_equipe_speciale_membre ON membre_equipe_speciale(membre_id) WHERE actif = true")
    op.execute("CREATE INDEX IF NOT EXISTS idx_membre_equipe_speciale_equipe ON membre_equipe_speciale(equipe_id) WHERE actif = true")
    op.execute("ALTER TABLE membre_equipe_speciale ENABLE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY membre_equipe_speciale_select ON membre_equipe_speciale FOR SELECT USING (adsum_current_role() = ANY({_LECTURE}))")
    op.execute(f"CREATE POLICY membre_equipe_speciale_write ON membre_equipe_speciale FOR ALL USING (adsum_current_role() = ANY({_COMITE})) WITH CHECK (adsum_current_role() = ANY({_COMITE}))")

    # Self-declaration flag (a person declares at registration; an admin confirms it
    # by adding a real membership row, the flag alone never grants anything).
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS equipe_dirigeante_declaree boolean NOT NULL DEFAULT false")

    # Seed the three known official teams (idempotent on the stable code).
    op.execute(
        """
        INSERT INTO equipe_speciale (code, nom, description, officielle, ordre) VALUES
            ('equipe_dirigeante', 'Équipe dirigeante', 'Instance de direction officielle de l''organisation.', true, 1),
            ('college_bergers', 'Collège des bergers', 'Collège officiel réunissant les bergers.', true, 2),
            ('assistants_fondateur', 'Groupe des assistants du fondateur', 'Groupe des assistants directs du fondateur.', true, 3)
        ON CONFLICT (code) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS equipe_dirigeante_declaree")
    op.execute("DROP TABLE IF EXISTS membre_equipe_speciale")
    op.execute("DROP TABLE IF EXISTS equipe_speciale")
    op.execute("DELETE FROM role_permission WHERE permission = 'organisation.equipes'")
    op.execute("DELETE FROM permission WHERE cle = 'organisation.equipes'")
