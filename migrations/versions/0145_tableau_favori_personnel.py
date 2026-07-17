# ruff: noqa: E501 - migrations carry long SQL lines
"""Make the board favourite a PERSONAL flag instead of a shared column.

``collab_tableau.favori`` was a single boolean on the board row: when one member starred a
board, every member of the space saw it starred and re-sorted, leaking a personal
preference into shared state. This migration introduces ``collab_tableau_favori`` (one row
per account per board) so each signed-in collaborator keeps their own stars.

The legacy shared column is left in place untouched (dropping a column the running API
still selects would break the deploy window); the API now computes ``favori`` from this
table and no longer reads or writes the legacy column. No data seeding: the legacy flag
cannot tell WHO starred a board, so carrying it over would force someone else's preference
onto every member. Stars simply restart empty, a one-click personal action.

Write policy includes 'membre': starring is a personal action available to any signed-in
collaborator, not only staff (the API guards remain permission + space role).

Revision ID: 0145_tableau_favori_personnel
Revises: 0144_evenement_cible_types
Create Date: 2026-07-17
"""
from __future__ import annotations

from alembic import op

revision = "0145_tableau_favori_personnel"
down_revision = "0144_evenement_cible_types"
branch_labels = None
depends_on = None

_ECRITURE = "ARRAY['super_admin', 'admin', 'gestionnaire', 'direction', 'membre']::text[]"
_LECTURE = "ARRAY['super_admin', 'admin', 'gestionnaire', 'direction', 'membre']::text[]"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE collab_tableau_favori (
            tableau_id uuid NOT NULL,
            utilisateur_id uuid NOT NULL,
            cree_le timestamptz DEFAULT now(),
            PRIMARY KEY (tableau_id, utilisateur_id)
        )
        """
    )
    op.execute("ALTER TABLE collab_tableau_favori ADD CONSTRAINT fk_collab_tableau_favori_tableau FOREIGN KEY (tableau_id) REFERENCES collab_tableau(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE collab_tableau_favori ADD CONSTRAINT fk_collab_tableau_favori_utilisateur FOREIGN KEY (utilisateur_id) REFERENCES utilisateur(id) ON DELETE CASCADE")
    op.execute("CREATE INDEX IF NOT EXISTS idx_collab_tableau_favori_utilisateur ON collab_tableau_favori(utilisateur_id)")
    op.execute("ALTER TABLE collab_tableau_favori ENABLE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY collab_tableau_favori_select ON collab_tableau_favori FOR SELECT USING (adsum_current_role() = ANY({_LECTURE}))")
    op.execute(f"CREATE POLICY collab_tableau_favori_write ON collab_tableau_favori FOR ALL USING (adsum_current_role() = ANY({_ECRITURE})) WITH CHECK (adsum_current_role() = ANY({_ECRITURE}))")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS collab_tableau_favori")
