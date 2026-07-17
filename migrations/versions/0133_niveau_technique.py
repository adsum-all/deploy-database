# ruff: noqa: E501 - migrations carry long SQL lines
"""Graduated privilege levels for technical (applicative) super-admin accounts.

A technical account now carries a ``niveau_technique`` (lecteur, developpeur,
mainteneur, admin, super) distinct from the member roles. The level governs who may
administer the technical-user roster and lifecycle: only ``admin`` and ``super`` may
create, activate, deactivate, relevel or delete other technical accounts, and only
``super`` may grant the ``super`` level or delete definitively. Existing technical
super-admins are set to ``super``. The column is NULL for non-technical accounts.

Revision ID: 0133_niveau_technique
Revises: 0132_type_evenement
Create Date: 2026-07-13
"""
from __future__ import annotations

from alembic import op

revision = "0133_niveau_technique"
down_revision = "0132_type_evenement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE utilisateur ADD COLUMN IF NOT EXISTS niveau_technique text")
    op.execute(
        "ALTER TABLE utilisateur DROP CONSTRAINT IF EXISTS utilisateur_niveau_technique_check"
    )
    op.execute(
        "ALTER TABLE utilisateur ADD CONSTRAINT utilisateur_niveau_technique_check "
        "CHECK (niveau_technique IS NULL OR niveau_technique IN "
        "('lecteur', 'developpeur', 'mainteneur', 'admin', 'super'))"
    )
    # Existing technical super-admins become the top level; no non-technical account is touched.
    op.execute(
        "UPDATE utilisateur SET niveau_technique = 'super' "
        "WHERE acces_technique_global = true AND niveau_technique IS NULL"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE utilisateur DROP CONSTRAINT IF EXISTS utilisateur_niveau_technique_check")
    op.execute("ALTER TABLE utilisateur DROP COLUMN IF EXISTS niveau_technique")
