# ruff: noqa: E501 - migrations carry long SQL and seeded text lines
"""Engagement levels as an admin-managed catalogue.

The engagement level of a member (``membre.type_membre``) was constrained by a
hard-coded CHECK, so adding or renaming a level required a code change. This
migration turns the levels into a catalogue table the administration owns
(create, rename, reorder, deactivate) and drops the CHECK so a new level can be
used immediately. The catalogue is advisory (like the honorific functions): a
level is soft-deactivated rather than deleted, so members already on it keep a
readable label.

Revision ID: 0064_niveau_engagement
Revises: 0063_patriarche_open_unique
Create Date: 2026-07-04
"""
from __future__ import annotations

from alembic import op

revision = "0064_niveau_engagement"
down_revision = "0063_patriarche_open_unique"
branch_labels = None
depends_on = None

# Existing levels, with their display label and hierarchical order. Seeded so the
# catalogue covers every value already stored on members.
_LEVELS = [
    ("membre_simple", "Membre simple", 10),
    ("nouveau_engage", "Nouvel engagé", 20),
    ("membre_actif", "Membre actif", 30),
    ("aspirant", "Aspirant", 40),
    ("engage", "Engagé", 50),
    ("inspirant", "Inspirant", 60),
    ("berger", "Berger", 70),
    ("responsable", "Responsable", 80),
]


def upgrade() -> None:
    # Free the column: the catalogue governs the allowed values from now on.
    op.execute("ALTER TABLE membre DROP CONSTRAINT IF EXISTS membre_type_membre_chk")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS niveau_engagement (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            cle text UNIQUE NOT NULL,
            libelle text NOT NULL,
            ordre integer NOT NULL DEFAULT 100,
            actif boolean NOT NULL DEFAULT true,
            cree_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("ALTER TABLE niveau_engagement ENABLE ROW LEVEL SECURITY")

    for cle, libelle, ordre in _LEVELS:
        op.execute(
            "INSERT INTO niveau_engagement (cle, libelle, ordre) SELECT %s, %s, %s "
            "WHERE NOT EXISTS (SELECT 1 FROM niveau_engagement WHERE cle = %s)",
            (cle, libelle, ordre, cle),
        )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS niveau_engagement")
    op.execute(
        "ALTER TABLE membre ADD CONSTRAINT membre_type_membre_chk "
        "CHECK (type_membre IN ('membre_simple','membre_actif','nouveau_engage','aspirant','engage','inspirant','berger','responsable'))"
    )
