# ruff: noqa: E501 - migrations carry long SQL lines
"""Availability floor: the base must always keep an active super_admin.

Defense in depth behind the service guard (which refuses removing the last
super_admin group or deactivating the last super_admin account, and blocks
super_admin self-removal). This statement-level trigger on ``utilisateur`` raises
if any UPDATE/DELETE would leave zero active super_admin, catching direct database
manipulation the application layer would not see.

Revision ID: 0077_guard_super_admin
Revises: 0076_groupe_permission
Create Date: 2026-07-06
"""
from __future__ import annotations

from alembic import op

revision = "0077_guard_super_admin"
down_revision = "0076_groupe_permission"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION adsum_guard_dernier_super_admin() RETURNS trigger AS $$
        BEGIN
            IF (SELECT count(*) FROM utilisateur WHERE role = 'super_admin' AND actif = true) = 0 THEN
                RAISE EXCEPTION 'au moins un super-administrateur actif doit exister';
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_dernier_super_admin ON utilisateur")
    op.execute(
        "CREATE TRIGGER trg_dernier_super_admin AFTER UPDATE OR DELETE ON utilisateur "
        "FOR EACH STATEMENT EXECUTE FUNCTION adsum_guard_dernier_super_admin()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_dernier_super_admin ON utilisateur")
    op.execute("DROP FUNCTION IF EXISTS adsum_guard_dernier_super_admin()")
