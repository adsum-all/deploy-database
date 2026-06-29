"""Per-role row level security policies for the 18 tables (Sprint 1, DB part).

Model (see ADR-0002): the FastAPI backend authenticates the user and sets a
session variable ``adsum.role`` to the caller role (utilisateur.role) for the
duration of the request transaction. RLS policies read it through the helper
``adsum_current_role()`` and apply the access matrix of the functional spec
(cahier section 5.2). The table owner (the backend connection role) and the
Supabase service role bypass RLS, so RLS is defense in depth, consistent with the
DAT decision that RBAC is enforced by the backend. Roles are not forced here, so
no existing access is broken.

Revision ID: 0005_rls_role_policies
Revises: 0004_indexes_partitions_rls
Create Date: 2026-06-28
"""
from __future__ import annotations

from alembic import op

revision = "0005_rls_role_policies"
down_revision = "0004_indexes_partitions_rls"
branch_labels = None
depends_on = None

STAFF = ["super_admin", "admin", "gestionnaire", "controleur", "direction"]

# table -> (roles allowed to SELECT, roles allowed to write INSERT/UPDATE/DELETE)
ACCESS: dict[str, tuple[list[str], list[str]]] = {
    "membre": (STAFF, ["super_admin", "admin"]),
    "commission": (STAFF, ["super_admin", "admin"]),
    "appartenance": (STAFF, ["super_admin", "admin"]),
    "engagement": (["super_admin", "admin"], ["super_admin", "admin"]),
    "document": (["super_admin", "admin"], ["super_admin", "admin"]),
    "evenement": (STAFF, ["super_admin", "admin", "gestionnaire"]),
    "presence": (
        ["super_admin", "admin", "gestionnaire", "controleur", "direction"],
        ["super_admin", "admin", "gestionnaire", "controleur"],
    ),
    "jeton_qr": (["super_admin", "admin", "gestionnaire", "controleur"], ["super_admin", "admin"]),
    "terminal": (["super_admin", "admin", "gestionnaire", "controleur"], ["super_admin", "admin"]),
    "comptage_volet_b": (
        ["super_admin", "admin", "gestionnaire", "direction"],
        ["super_admin", "admin", "gestionnaire", "controleur"],
    ),
    "utilisateur": (["super_admin"], ["super_admin"]),
    "session": (["super_admin"], ["super_admin"]),
    "audit": (["super_admin", "admin"], []),  # append-only, no write through app
    "notification": (STAFF, ["super_admin", "admin"]),
    "parametre": (STAFF, ["super_admin"]),
    "import_lot": (["super_admin", "admin"], ["super_admin", "admin"]),
    "recensement": (STAFF, ["super_admin", "admin", "gestionnaire"]),
    "recensement_reponse": (
        ["super_admin", "admin", "gestionnaire", "direction"],
        ["super_admin", "admin"],
    ),
}


def _array(roles: list[str]) -> str:
    inner = ", ".join(f"'{r}'" for r in roles)
    return f"ARRAY[{inner}]::text[]"


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION adsum_current_role() RETURNS text
        LANGUAGE sql STABLE AS $$
            SELECT current_setting('adsum.role', true)
        $$
        """
    )
    for table, (select_roles, write_roles) in ACCESS.items():
        op.execute(
            f"CREATE POLICY {table}_select ON {table} FOR SELECT "
            f"USING (adsum_current_role() = ANY({_array(select_roles)}))"
        )
        if write_roles:
            op.execute(
                f"CREATE POLICY {table}_write ON {table} FOR ALL "
                f"USING (adsum_current_role() = ANY({_array(write_roles)})) "
                f"WITH CHECK (adsum_current_role() = ANY({_array(write_roles)}))"
            )


def downgrade() -> None:
    for table, (_, write_roles) in ACCESS.items():
        op.execute(f"DROP POLICY IF EXISTS {table}_select ON {table}")
        if write_roles:
            op.execute(f"DROP POLICY IF EXISTS {table}_write ON {table}")
    op.execute("DROP FUNCTION IF EXISTS adsum_current_role()")
