# ruff: noqa: E501 - migrations carry long SQL lines
"""Complete row-level security coverage on the tables that shipped without it.

A deep audit found seven tables with RLS never enabled (the three moderator-channel
tables from 0110, plus collab_item_assigne, collab_presence, evenement_piece and
notification_echec), and niveau_engagement (0064) which enabled RLS but never
created a policy. This migration enables RLS on the seven and adds role policies,
so every one of these tables is both RLS-enabled and policied.

Safety: the application connects as the table owner and therefore bypasses RLS
(verified: niveau_engagement already had RLS enabled with no policy, i.e. deny for
any non-owner, yet the back office reads and writes it normally). These policies
are pure defense in depth against a hypothetical non-owner connection; anon and
authenticated were already revoked by 0042. No application access path changes.

Revision ID: 0116_rls_niveau_canal
Revises: 0115_canal_piece_note_fk
Create Date: 2026-07-11
"""
from __future__ import annotations

from alembic import op

revision = "0116_rls_niveau_canal"
down_revision = "0115_canal_piece_note_fk"
branch_labels = None
depends_on = None

# niveau_engagement: read for every role that can consult it, write for those who
# manage it (mirrors niveaux-engagement.consulter / .gerer in the RBAC catalogue).
_NIV_SELECT = "ARRAY['super_admin', 'admin', 'gestionnaire', 'direction', 'controleur']::text[]"
_NIV_WRITE = "ARRAY['super_admin', 'admin', 'gestionnaire']::text[]"

# Staff role-sets mirroring the other collab_* tables (see 0097): read for the
# committee roles plus direction, write for the committee.
_LECTURE = "ARRAY['super_admin', 'admin', 'gestionnaire', 'direction']::text[]"
_COMITE = "ARRAY['super_admin', 'admin', 'gestionnaire']::text[]"

# Tables that had RLS disabled entirely: enable it and add staff policies.
_ENABLE_TABLES = [
    "collab_canal_message",
    "collab_canal_note",
    "collab_canal_reponse",
    "collab_item_assigne",
    "collab_presence",
    "evenement_piece",
    "notification_echec",
]


def upgrade() -> None:
    # niveau_engagement already has RLS enabled (0064); only the policies were missing.
    op.execute(f"CREATE POLICY niveau_engagement_select ON niveau_engagement FOR SELECT USING (adsum_current_role() = ANY({_NIV_SELECT}))")
    op.execute(f"CREATE POLICY niveau_engagement_write ON niveau_engagement FOR ALL USING (adsum_current_role() = ANY({_NIV_WRITE})) WITH CHECK (adsum_current_role() = ANY({_NIV_WRITE}))")
    for table in _ENABLE_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY {table}_select ON {table} FOR SELECT USING (adsum_current_role() = ANY({_LECTURE}))")
        op.execute(f"CREATE POLICY {table}_write ON {table} FOR ALL USING (adsum_current_role() = ANY({_COMITE})) WITH CHECK (adsum_current_role() = ANY({_COMITE}))")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS niveau_engagement_write ON niveau_engagement")
    op.execute("DROP POLICY IF EXISTS niveau_engagement_select ON niveau_engagement")
    for table in _ENABLE_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_write ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_select ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
