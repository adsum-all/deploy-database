# ruff: noqa: E501 - migrations carry long SQL and seeded text lines
"""Patriarche as a resolved person, not a fixed label.

Until now ``tribu.patriarche`` held a fixed text (the biblical foundation of the
tribe, e.g. "Juda, fils de Jacob et Lea"). That text was shown in the member
"Patriarche" field, which is wrong: a patriarche is a function held by a real
member for a given tribe, at most one active at a time, and it can change. This
migration adds ``tribu.patriarche_membre_id`` (the current human titulaire, at
most one per tribe by construction since a tribe is a single row) and a history
table that keeps every appointment and revocation for audit. The old text stays
as the tribe's biblical reference; it is displayed separately, never as the
current patriarche.

Revision ID: 0062_patriarche_personne
Revises: 0061_org_type_parent
Create Date: 2026-07-04
"""
from __future__ import annotations

from alembic import op

revision = "0062_patriarche_personne"
down_revision = "0061_org_type_parent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Current human patriarche of the tribe (at most one: a tribe is one row).
    op.execute("ALTER TABLE tribu ADD COLUMN IF NOT EXISTS patriarche_membre_id uuid")
    op.execute("ALTER TABLE tribu DROP CONSTRAINT IF EXISTS tribu_patriarche_membre_fk")
    op.execute("ALTER TABLE tribu ADD CONSTRAINT tribu_patriarche_membre_fk FOREIGN KEY (patriarche_membre_id) REFERENCES membre(id) ON DELETE SET NULL")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tribu_patriarche_membre ON tribu(patriarche_membre_id)")

    # Full history of the patriarche function per tribe, for audit and to answer
    # "who was patriarche of which tribe, from when to when, set by whom, why".
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tribu_patriarche_historique (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tribu_id uuid NOT NULL,
            membre_id uuid NOT NULL,
            debut timestamptz NOT NULL DEFAULT now(),
            fin timestamptz,
            attribue_par uuid,
            motif text,
            cree_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("ALTER TABLE tribu_patriarche_historique DROP CONSTRAINT IF EXISTS tph_tribu_fk")
    op.execute("ALTER TABLE tribu_patriarche_historique ADD CONSTRAINT tph_tribu_fk FOREIGN KEY (tribu_id) REFERENCES tribu(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE tribu_patriarche_historique DROP CONSTRAINT IF EXISTS tph_membre_fk")
    op.execute("ALTER TABLE tribu_patriarche_historique ADD CONSTRAINT tph_membre_fk FOREIGN KEY (membre_id) REFERENCES membre(id) ON DELETE CASCADE")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tph_tribu ON tribu_patriarche_historique(tribu_id)")
    op.execute("ALTER TABLE tribu_patriarche_historique ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tribu_patriarche_historique")
    op.execute("DROP INDEX IF EXISTS idx_tribu_patriarche_membre")
    op.execute("ALTER TABLE tribu DROP CONSTRAINT IF EXISTS tribu_patriarche_membre_fk")
    op.execute("ALTER TABLE tribu DROP COLUMN IF EXISTS patriarche_membre_id")
