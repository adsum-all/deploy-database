# ruff: noqa: E501 - migrations carry long SQL and seeded text lines
"""Enforce a single open patriarche history line per tribe.

Belt-and-suspenders for the appointment endpoint: at most one history line may be
open (``fin IS NULL``) per tribe at any time. Two concurrent appointments can no
longer both leave an open line; the second insert fails at the database level.

Revision ID: 0063_patriarche_open_unique
Revises: 0062_patriarche_personne
Create Date: 2026-07-04
"""
from __future__ import annotations

from alembic import op

revision = "0063_patriarche_open_unique"
down_revision = "0062_patriarche_personne"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Close any accidental duplicate open lines before enforcing the invariant,
    # keeping only the most recent open line per tribe.
    op.execute(
        """
        UPDATE tribu_patriarche_historique h
        SET fin = now()
        WHERE fin IS NULL
          AND id <> (
            SELECT h2.id FROM tribu_patriarche_historique h2
            WHERE h2.tribu_id = h.tribu_id AND h2.fin IS NULL
            ORDER BY h2.debut DESC, h2.cree_le DESC
            LIMIT 1
          )
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_tph_open_par_tribu ON tribu_patriarche_historique (tribu_id) WHERE fin IS NULL")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_tph_open_par_tribu")
