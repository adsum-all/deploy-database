"""Object-storage backing for collaboration card/comment attachments.

Mirrors evenement_piece.storage_path (migration 0104): when the API is configured
with a private bucket, an attachment is uploaded as an object and this column holds
its storage path (the row's url is then empty and a signed URL is served); when the
column is NULL the attachment keeps its inline data URL. Existing rows are untouched.

Revision ID: 0105_collab_piece_storage
Revises: 0104_evenement_piece_storage
"""
from __future__ import annotations

from alembic import op

revision = "0105_collab_piece_storage"
down_revision = "0104_evenement_piece_storage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE collab_piece ADD COLUMN IF NOT EXISTS storage_path text")


def downgrade() -> None:
    op.execute("ALTER TABLE collab_piece DROP COLUMN IF EXISTS storage_path")
