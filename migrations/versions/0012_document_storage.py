"""Link member documents to Supabase Storage objects.

Adds the storage path, original filename and mime type to ``document`` so an
uploaded identity piece / consent is connected to its private object in the
``member-documents`` bucket. The profile photo path reuses ``membre.photo_url``.

Revision ID: 0012_document_storage
Revises: 0011_demandes_conversation
Create Date: 2026-06-30
"""
from __future__ import annotations

from alembic import op

revision = "0012_document_storage"
down_revision = "0011_demandes_conversation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE document ADD COLUMN IF NOT EXISTS chemin_stockage text")
    op.execute("ALTER TABLE document ADD COLUMN IF NOT EXISTS nom_fichier text")
    op.execute("ALTER TABLE document ADD COLUMN IF NOT EXISTS mime text")
    op.execute("ALTER TABLE document ADD COLUMN IF NOT EXISTS bucket text")


def downgrade() -> None:
    op.execute("ALTER TABLE document DROP COLUMN IF EXISTS chemin_stockage")
    op.execute("ALTER TABLE document DROP COLUMN IF EXISTS nom_fichier")
    op.execute("ALTER TABLE document DROP COLUMN IF EXISTS mime")
    op.execute("ALTER TABLE document DROP COLUMN IF EXISTS bucket")
