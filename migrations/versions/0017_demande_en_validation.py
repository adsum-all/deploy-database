"""Add the 'en_validation' status to member requests.

When a member submits edits on admin-unlocked fields, the request moves to
'en_validation': the proposed values wait for the administration's final
validation before they are committed to the member record.

Revision ID: 0017_demande_en_validation
Revises: 0016_modification_membre
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0017_demande_en_validation"
down_revision = "0016_modification_membre"
branch_labels = None
depends_on = None

_NEW = "('ouverte', 'en_cours', 'en_validation', 'resolue', 'refusee')"
_OLD = "('ouverte', 'en_cours', 'resolue', 'refusee')"


def upgrade() -> None:
    op.execute("ALTER TABLE demande DROP CONSTRAINT IF EXISTS demande_statut_chk")
    op.execute(f"ALTER TABLE demande ADD CONSTRAINT demande_statut_chk CHECK (statut IN {_NEW})")


def downgrade() -> None:
    op.execute("ALTER TABLE demande DROP CONSTRAINT IF EXISTS demande_statut_chk")
    op.execute(f"ALTER TABLE demande ADD CONSTRAINT demande_statut_chk CHECK (statut IN {_OLD})")
