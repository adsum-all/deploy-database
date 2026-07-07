"""Add a per-member display theme preference (light / dark / system).

The member app was locked to light. This adds a stored preference so a member can
choose light, dark, or follow their device (system). Default stays 'light', so
nothing changes for existing members until they opt in, honouring the rule that
the app is never dark by default.

Revision ID: 0093_membre_theme
Revises: 0092_fonction_famille_niveau
"""
from __future__ import annotations

from alembic import op

revision = "0093_membre_theme"
down_revision = "0092_fonction_famille_niveau"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS theme text NOT NULL DEFAULT 'light'")
    op.execute("ALTER TABLE membre ADD CONSTRAINT membre_theme_chk CHECK (theme IN ('light', 'dark', 'system'))")


def downgrade() -> None:
    op.execute("ALTER TABLE membre DROP CONSTRAINT IF EXISTS membre_theme_chk")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS theme")
