# ruff: noqa: E501 - migrations carry long SQL lines
"""Seed the fine-grained channel permissions in the permission catalogue table.

The Python catalogue (app.permissions_data) already declares canal.voir / .traiter
/ .administrer; the DB permission table must mirror them so a permissions group can
reference them (groupe_permission.permission is a FK to permission.cle).

Revision ID: 0123_canal_permissions
Revises: 0122_colonne_instructions
Create Date: 2026-07-11
"""
from __future__ import annotations

from alembic import op

revision = "0123_canal_permissions"
down_revision = "0122_colonne_instructions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO permission (cle, domaine, libelle, risque, portee, systeme) VALUES
          ('canal.voir', 'canal', 'Canal - voir les instructions', 'moyen', 'global', true),
          ('canal.traiter', 'canal', 'Canal - traiter les instructions', 'eleve', 'global', true),
          ('canal.administrer', 'canal', 'Canal - administrer', 'critique', 'global', true)
        ON CONFLICT (cle) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM permission WHERE cle IN ('canal.voir', 'canal.traiter', 'canal.administrer')")
