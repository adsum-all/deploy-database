"""Electronic signature of the consent documents.

Adds a ``signature_engagement`` table that records one signing event (the set of
documents and versions the member signed, the channels used, the request context
kept as legal evidence, whether the one-time code was verified, and a proof
hash). Also extends ``engagement`` with the signature context (ip, canal,
code_verifie) and a link back to the signing event (signature_id), so each signed
document keeps its own evidence while the ceremony is grouped in one row.

Revision ID: 0033_esignature
Revises: 0032_consent_docs
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0033_esignature"
down_revision = "0032_consent_docs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS signature_engagement (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            membre_id uuid REFERENCES membre(id) ON DELETE CASCADE,
            documents jsonb NOT NULL DEFAULT '[]',
            canaux text,
            ip text,
            session_id text,
            user_agent text,
            code_verifie boolean NOT NULL DEFAULT false,
            hash_preuve text,
            cree_le timestamptz DEFAULT now(),
            signe_le timestamptz
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_signature_engagement_membre ON signature_engagement (membre_id)")
    op.execute(
        """
        ALTER TABLE engagement
            ADD COLUMN IF NOT EXISTS ip text,
            ADD COLUMN IF NOT EXISTS canal text,
            ADD COLUMN IF NOT EXISTS code_verifie boolean,
            ADD COLUMN IF NOT EXISTS signature_id uuid
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE engagement
            DROP COLUMN IF EXISTS ip,
            DROP COLUMN IF EXISTS canal,
            DROP COLUMN IF EXISTS code_verifie,
            DROP COLUMN IF EXISTS signature_id
        """
    )
    op.execute("DROP INDEX IF EXISTS idx_signature_engagement_membre")
    op.execute("DROP TABLE IF EXISTS signature_engagement")
