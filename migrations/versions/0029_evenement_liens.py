"""Multiple broadcast links per session.

An event can be broadcast on several platforms at once (for instance Zoom and
Telegram). The links are stored as a JSON array; the platform of each link is
detected client-side from its URL. The legacy single lien_session is kept as the
primary link for backward compatibility and is seeded from any existing value.

Revision ID: 0029_evenement_liens
Revises: 0028_evenement_diffusion
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0029_evenement_liens"
down_revision = "0028_evenement_diffusion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE evenement ADD COLUMN IF NOT EXISTS liens jsonb NOT NULL DEFAULT '[]'::jsonb")
    # Seed the array from the existing single link so nothing is lost.
    op.execute(
        "UPDATE evenement SET liens = jsonb_build_array(lien_session) "
        "WHERE lien_session IS NOT NULL AND lien_session <> '' AND liens = '[]'::jsonb"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE evenement DROP COLUMN IF EXISTS liens")
