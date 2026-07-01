"""Mark identity documents that are encrypted at rest.

Identity documents are now encrypted with an application-controlled key before
they land in the private bucket (see app/crypto.py). These columns record that a
document's bytes are ciphertext and which algorithm produced them, so the API
knows to decrypt on an authorised, audited read.

Revision ID: 0040_document_chiffrement
Revises: 0039_retention_conservation
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0040_document_chiffrement"
down_revision = "0039_retention_conservation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE document ADD COLUMN IF NOT EXISTS chiffre boolean NOT NULL DEFAULT false")
    op.execute("ALTER TABLE document ADD COLUMN IF NOT EXISTS chiffrement_algo text")


def downgrade() -> None:
    op.execute("ALTER TABLE document DROP COLUMN IF EXISTS chiffrement_algo")
    op.execute("ALTER TABLE document DROP COLUMN IF EXISTS chiffre")
