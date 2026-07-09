"""Optional object-storage backing for activity attachments.

When the API is configured with a private bucket (ADSUM_STORAGE_BUCKET_EVENEMENTS),
an attachment is uploaded as an object and this column holds its storage path; the
API then serves a short-lived signed URL instead of the inline data URL, keeping
base64 blobs out of the database. When the column is NULL the attachment keeps its
inline data URL (backward compatible: existing rows are untouched).

Revision ID: 0104_evenement_piece_storage
Revises: 0103_evenement_piece
"""
from __future__ import annotations

from alembic import op

revision = "0104_evenement_piece_storage"
down_revision = "0103_evenement_piece"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE evenement_piece ADD COLUMN IF NOT EXISTS storage_path text")


def downgrade() -> None:
    op.execute("ALTER TABLE evenement_piece DROP COLUMN IF EXISTS storage_path")
