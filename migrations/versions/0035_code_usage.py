"""Single-use one-time codes: consume a code atomically on success.

The one-time codes are HMAC-derived (stateless) and were replay-tolerant within
their time window. This adds a consumption ledger so a code that was used once
becomes permanently invalid: the unique constraint makes the verify-and-consume
step atomic, so the same code can never succeed twice, even under concurrency.

Revision ID: 0035_code_usage
Revises: 0034_pays_attestation
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0035_code_usage"
down_revision = "0034_pays_attestation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS code_consomme (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            email text NOT NULL,
            purpose text NOT NULL,
            code_hash text NOT NULL,
            ip text,
            consomme_le timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT code_consomme_uq UNIQUE (email, purpose, code_hash)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_code_consomme_when ON code_consomme (consomme_le)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS code_consomme")
