"""Collaboration space for the committee (Trello-like board).

Adds the boards, columns, cards (preparation sheets), comments (real-time chat by
polling) and card versions used by the committee collaboration app (interface E).
A prepared card can be published as an ``evenement`` and open its check-in
session. Access is restricted to the committee roles (super_admin, admin,
gestionnaire); direction may read. RLS follows the existing matrix (ADR-0002).

Revision ID: 0009_collaboration
Revises: 0008_member_identity_engagement
Create Date: 2026-06-30
"""
from __future__ import annotations

from alembic import op

revision = "0009_collaboration"
down_revision = "0008_member_identity_engagement"
branch_labels = None
depends_on = None

COMITE = "ARRAY['super_admin', 'admin', 'gestionnaire']::text[]"
LECTURE = "ARRAY['super_admin', 'admin', 'gestionnaire', 'direction']::text[]"

TABLES = ("collab_tableau", "collab_colonne", "collab_carte", "collab_commentaire", "collab_version")


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE collab_tableau (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            nom text NOT NULL,
            description text,
            archive boolean NOT NULL DEFAULT false,
            cree_par uuid,
            cree_le timestamptz DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE collab_colonne (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tableau_id uuid NOT NULL REFERENCES collab_tableau(id) ON DELETE CASCADE,
            nom text NOT NULL,
            position int NOT NULL DEFAULT 0,
            cree_le timestamptz DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE collab_carte (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tableau_id uuid NOT NULL REFERENCES collab_tableau(id) ON DELETE CASCADE,
            colonne_id uuid NOT NULL REFERENCES collab_colonne(id) ON DELETE CASCADE,
            titre text NOT NULL,
            description text,
            type_activite text,
            date_prevue timestamptz,
            lieu text,
            position int NOT NULL DEFAULT 0,
            publie boolean NOT NULL DEFAULT false,
            evenement_id uuid REFERENCES evenement(id) ON DELETE SET NULL,
            cree_par uuid,
            cree_le timestamptz DEFAULT now(),
            maj_le timestamptz DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE collab_commentaire (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            carte_id uuid NOT NULL REFERENCES collab_carte(id) ON DELETE CASCADE,
            auteur_id uuid,
            auteur_nom text,
            corps text NOT NULL,
            cree_le timestamptz DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE collab_version (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            carte_id uuid NOT NULL REFERENCES collab_carte(id) ON DELETE CASCADE,
            snapshot jsonb NOT NULL,
            auteur_id uuid,
            auteur_nom text,
            cree_le timestamptz DEFAULT now()
        )
        """
    )

    op.execute("CREATE INDEX idx_collab_colonne_tableau ON collab_colonne(tableau_id)")
    op.execute("CREATE INDEX idx_collab_carte_colonne ON collab_carte(colonne_id)")
    op.execute("CREATE INDEX idx_collab_carte_tableau ON collab_carte(tableau_id)")
    op.execute("CREATE INDEX idx_collab_commentaire_carte ON collab_commentaire(carte_id)")
    op.execute("CREATE INDEX idx_collab_version_carte ON collab_version(carte_id)")

    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_select ON {table} FOR SELECT "
            f"USING (adsum_current_role() = ANY({LECTURE}))"
        )
        op.execute(
            f"CREATE POLICY {table}_write ON {table} FOR ALL "
            f"USING (adsum_current_role() = ANY({COMITE})) "
            f"WITH CHECK (adsum_current_role() = ANY({COMITE}))"
        )


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_select ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_write ON {table}")
    op.execute("DROP TABLE IF EXISTS collab_version CASCADE")
    op.execute("DROP TABLE IF EXISTS collab_commentaire CASCADE")
    op.execute("DROP TABLE IF EXISTS collab_carte CASCADE")
    op.execute("DROP TABLE IF EXISTS collab_colonne CASCADE")
    op.execute("DROP TABLE IF EXISTS collab_tableau CASCADE")
