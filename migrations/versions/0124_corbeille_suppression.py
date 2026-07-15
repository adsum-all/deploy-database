# ruff: noqa: E501 - migrations carry long SQL lines
"""Deferred definitive deletion (trash) for workspaces and boards.

Beyond archiving, a workspace, sub-space or board can be sent to the trash
(soft-deleted). It stays recoverable for a configurable number of days
(retention_suppression_jours, 0-90, default 14) and is then purged for good by the
daily job. A retention of 0 means the deletion is immediate.

Revision ID: 0124_corbeille_suppression
Revises: 0123_canal_permissions
Create Date: 2026-07-11
"""
from __future__ import annotations

from alembic import op

revision = "0124_corbeille_suppression"
down_revision = "0123_canal_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("collab_espace", "collab_tableau"):
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS supprime_le timestamptz")
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS supprime_par uuid REFERENCES utilisateur(id) ON DELETE SET NULL")
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_{table}_corbeille ON {table} (supprime_le) WHERE supprime_le IS NOT NULL")
    op.execute(
        """
        INSERT INTO parametre (cle, valeur, categorie, description)
        VALUES ('retention_suppression_jours', '14'::jsonb, 'collaboration',
                'Nombre de jours (0 a 90) pendant lesquels un espace, sous-espace ou tableau supprime reste recuperable avant purge definitive. 0 = suppression immediate.')
        ON CONFLICT (cle) DO NOTHING
        """
    )


def downgrade() -> None:
    for table in ("collab_espace", "collab_tableau"):
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_corbeille")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS supprime_par")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS supprime_le")
    op.execute("DELETE FROM parametre WHERE cle = 'retention_suppression_jours'")
