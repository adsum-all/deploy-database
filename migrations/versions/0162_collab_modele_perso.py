# ruff: noqa: E501 - migrations carry long SQL lines
"""Custom board templates + the permission that gates their creation.

Teams can build their own reusable board templates in the collaboration app, on top
of the built-in catalogue. Two pieces:

- ``collaboration.modeles``: a new permission that gates the template BUILDER page. It
  is held by super_admin and admin by default, and can be granted to any member through
  a governance group (mode 'permissions'), so only that special role sees the page.
- ``collab_modele_perso``: stores a custom template as its column structure (jsonb, the
  exact shape the board creator already consumes), scoped to a workspace, soft-deletable.
  Deleting a template never touches boards already created from it (columns are copied).

Revision ID: 0162_collab_modele_perso
Revises: 0161_information_affiche_entete
Create Date: 2026-07-19
"""
from __future__ import annotations

from alembic import op

revision = "0162_collab_modele_perso"
down_revision = "0161_information_affiche_entete"
branch_labels = None
depends_on = None

_COMITE = "ARRAY['super_admin', 'admin', 'gestionnaire']::text[]"
_LECTURE = "ARRAY['super_admin', 'admin', 'gestionnaire', 'direction']::text[]"


def upgrade() -> None:
    # The permission must exist in the catalogue before any group can reference it
    # (groupe_permission.permission is a FK to permission.cle).
    op.execute(
        "INSERT INTO permission (cle, domaine, libelle, risque, portee, systeme) "
        "VALUES ('collaboration.modeles', 'collaboration', 'Collaboration - modeles de tableaux', 'moyen', 'global', true) "
        "ON CONFLICT (cle) DO NOTHING"
    )
    op.execute(
        "INSERT INTO role_permission (role, permission) "
        "SELECT r, 'collaboration.modeles' FROM (VALUES ('super_admin'), ('admin')) AS v(r) "
        "ON CONFLICT DO NOTHING"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collab_modele_perso (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            espace_id uuid NOT NULL REFERENCES collab_espace(id) ON DELETE CASCADE,
            nom text NOT NULL,
            description text NOT NULL DEFAULT '',
            structure jsonb NOT NULL DEFAULT '[]'::jsonb,
            visibilite text NOT NULL DEFAULT 'espace',
            cree_par uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            cree_le timestamptz NOT NULL DEFAULT now(),
            maj_le timestamptz NOT NULL DEFAULT now(),
            supprime_le timestamptz,
            CONSTRAINT collab_modele_perso_visibilite_chk CHECK (visibilite IN ('espace', 'prive'))
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_collab_modele_perso_espace ON collab_modele_perso(espace_id) WHERE supprime_le IS NULL")
    op.execute("ALTER TABLE collab_modele_perso ENABLE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY collab_modele_perso_select ON collab_modele_perso FOR SELECT USING (adsum_current_role() = ANY({_LECTURE}))")
    op.execute(f"CREATE POLICY collab_modele_perso_write ON collab_modele_perso FOR ALL USING (adsum_current_role() = ANY({_COMITE})) WITH CHECK (adsum_current_role() = ANY({_COMITE}))")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS collab_modele_perso")
    op.execute("DELETE FROM role_permission WHERE permission = 'collaboration.modeles'")
    op.execute("DELETE FROM permission WHERE cle = 'collaboration.modeles'")
