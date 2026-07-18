# ruff: noqa: E501 - migrations carry long SQL lines
"""Row level security for the organisation-chart tables (0150).

Keeps the RLS coverage at 100 percent: every organisation_* table gets a read
policy for the authenticated roles and a write policy restricted to the platform
administrators, mirroring the referential pattern (0147). The API connects as the
schema owner and bypasses these non-FORCE policies; they are defence in depth
against any other role.

Revision ID: 0151_organigramme_rls
Revises: 0150_organisation_org
Create Date: 2026-07-18
"""
from __future__ import annotations

from alembic import op

revision = "0151_organigramme_rls"
down_revision = "0150_organisation_org"
branch_labels = None
depends_on = None

_LECTURE = "ARRAY['super_admin', 'admin', 'gestionnaire', 'direction', 'membre', 'controleur']::text[]"
_ECRITURE = "ARRAY['super_admin', 'admin']::text[]"
_TABLES = ("organisation_version", "organisation_node", "organisation_link", "organisation_changelog")


def upgrade() -> None:
    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        # The change log is admin-only for reading; the graph tables are readable by
        # every authenticated role (members consult the published chart).
        lecture = _ECRITURE if table == "organisation_changelog" else _LECTURE
        op.execute(f"DROP POLICY IF EXISTS {table}_select ON {table}")
        op.execute(f"CREATE POLICY {table}_select ON {table} FOR SELECT USING (adsum_current_role() = ANY({lecture}))")
        op.execute(f"DROP POLICY IF EXISTS {table}_write ON {table}")
        op.execute(f"CREATE POLICY {table}_write ON {table} FOR ALL USING (adsum_current_role() = ANY({_ECRITURE})) WITH CHECK (adsum_current_role() = ANY({_ECRITURE}))")


def downgrade() -> None:
    for table in _TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_write ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_select ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
