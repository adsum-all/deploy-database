# ruff: noqa: E501 - migrations carry long SQL and seeded text lines
"""Session end and audit geolocation.

Logins were tracked (ip, device, time) but logouts were not, so a session had no
end and no duration. This adds ``fin`` (the logout or revocation time) and a
coarse audit geolocation (country, city, region) resolved from the edge headers
at login. The geolocation is deliberately country/city level: it is realistic
and useful for a security audit without claiming a misleading precision.

Revision ID: 0065_session_fin_geo
Revises: 0064_niveau_engagement
Create Date: 2026-07-05
"""
from __future__ import annotations

from alembic import op

revision = "0065_session_fin_geo"
down_revision = "0064_niveau_engagement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE session ADD COLUMN IF NOT EXISTS fin timestamptz")
    op.execute("ALTER TABLE session ADD COLUMN IF NOT EXISTS pays text")
    op.execute("ALTER TABLE session ADD COLUMN IF NOT EXISTS ville text")
    op.execute("ALTER TABLE session ADD COLUMN IF NOT EXISTS region text")
    op.execute("CREATE INDEX IF NOT EXISTS idx_session_utilisateur ON session(utilisateur_id, cree_le DESC)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_session_utilisateur")
    op.execute("ALTER TABLE session DROP COLUMN IF EXISTS region")
    op.execute("ALTER TABLE session DROP COLUMN IF EXISTS ville")
    op.execute("ALTER TABLE session DROP COLUMN IF EXISTS pays")
    op.execute("ALTER TABLE session DROP COLUMN IF EXISTS fin")
