"""Authentication attempt log for brute-force rate limiting.

Each hit on a sensitive auth endpoint (login, OTP request, password reset) is
recorded with the caller IP. A sliding-window count over this table lets the API
reject bursts (OWASP brute-force protection) even on a stateless serverless
runtime where in-memory counters do not persist between invocations.

Revision ID: 0021_auth_attempt
Revises: 0020_formation_questionnaire
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0021_auth_attempt"
down_revision = "0020_formation_questionnaire"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_attempt (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            ip inet,
            endpoint text NOT NULL,
            cree_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_auth_attempt_window ON auth_attempt (ip, endpoint, cree_le)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS auth_attempt")
