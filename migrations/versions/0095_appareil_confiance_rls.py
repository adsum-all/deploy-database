"""Harden appareil_confiance: enable RLS and revoke anon/authenticated.

Matches the security posture of the other sensitive tables (session, etc.): the
application connects as the table owner and bypasses RLS, so this does not affect
the app, but it keeps the table closed to the Supabase anon/authenticated roles
and consistent with the 100% RLS coverage established earlier.

Revision ID: 0095_appareil_confiance_rls
Revises: 0094_mfa_2fa
"""
from __future__ import annotations

from alembic import op

revision = "0095_appareil_confiance_rls"
down_revision = "0094_mfa_2fa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ENABLE (not FORCE): the application connects as the table owner and keeps
    # bypassing RLS (same as the session table), while non-owner roles are denied.
    op.execute("ALTER TABLE appareil_confiance ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON appareil_confiance FROM anon, authenticated")


def downgrade() -> None:
    op.execute("ALTER TABLE appareil_confiance DISABLE ROW LEVEL SECURITY")
