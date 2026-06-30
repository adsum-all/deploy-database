"""Allow the 'membre' role on utilisateur.

Real member accounts (created by the admin during registration) use the
``membre`` role, which the original 0002 check constraint did not permit. The
member role grants no staff access (member endpoints gate on ``membre_id``,
staff endpoints gate on the staff roles), so this only widens the allowed set.

Revision ID: 0014_role_membre
Revises: 0013_inscription_workflow
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0014_role_membre"
down_revision = "0013_inscription_workflow"
branch_labels = None
depends_on = None

ROLES = ("super_admin", "admin", "gestionnaire", "controleur", "direction", "membre")


def upgrade() -> None:
    roles = ", ".join(f"'{r}'" for r in ROLES)
    op.execute("ALTER TABLE utilisateur DROP CONSTRAINT IF EXISTS utilisateur_role_chk")
    op.execute(f"ALTER TABLE utilisateur ADD CONSTRAINT utilisateur_role_chk CHECK (role IN ({roles}))")


def downgrade() -> None:
    roles = ", ".join(f"'{r}'" for r in ROLES if r != "membre")
    op.execute("ALTER TABLE utilisateur DROP CONSTRAINT IF EXISTS utilisateur_role_chk")
    op.execute(f"ALTER TABLE utilisateur ADD CONSTRAINT utilisateur_role_chk CHECK (role IN ({roles}))")
