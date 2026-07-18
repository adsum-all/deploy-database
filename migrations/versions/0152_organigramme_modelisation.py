# ruff: noqa: E501 - migrations carry long SQL lines
"""Modeling tools for the organisation chart: node styling and free elements.

Turns the chart into a real modeling surface. Nodes gain a colour and a photo
toggle, and free dimensions so a node can also be a separator line or a labelled
zone. The type set is widened accordingly (separateur, note, zone) while keeping
the existing person/structure/group values.

Revision ID: 0152_organigramme_model
Revises: 0151_organigramme_rls
Create Date: 2026-07-18
"""
from __future__ import annotations

from alembic import op

revision = "0152_organigramme_model"
down_revision = "0151_organigramme_rls"
branch_labels = None
depends_on = None

_TYPES_NOEUD = ("personne", "structure", "groupe", "separateur", "note", "zone")


def upgrade() -> None:
    op.execute("ALTER TABLE organisation_node ADD COLUMN IF NOT EXISTS couleur text")
    op.execute("ALTER TABLE organisation_node ADD COLUMN IF NOT EXISTS afficher_photo boolean NOT NULL DEFAULT false")
    op.execute("ALTER TABLE organisation_node ADD COLUMN IF NOT EXISTS largeur double precision")
    op.execute("ALTER TABLE organisation_node ADD COLUMN IF NOT EXISTS hauteur double precision")
    # Widen the node-type check to allow the free modeling elements.
    op.execute("ALTER TABLE organisation_node DROP CONSTRAINT IF EXISTS organisation_node_type_noeud_check")
    valeurs = ", ".join(f"'{t}'" for t in _TYPES_NOEUD)
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'organisation_node_type_noeud_check') THEN "
        f"ALTER TABLE organisation_node ADD CONSTRAINT organisation_node_type_noeud_check CHECK (type_noeud IN ({valeurs})); "
        "END IF; END $$;"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE organisation_node DROP CONSTRAINT IF EXISTS organisation_node_type_noeud_check")
    op.execute("ALTER TABLE organisation_node DROP COLUMN IF EXISTS hauteur")
    op.execute("ALTER TABLE organisation_node DROP COLUMN IF EXISTS largeur")
    op.execute("ALTER TABLE organisation_node DROP COLUMN IF EXISTS afficher_photo")
    op.execute("ALTER TABLE organisation_node DROP COLUMN IF EXISTS couleur")
