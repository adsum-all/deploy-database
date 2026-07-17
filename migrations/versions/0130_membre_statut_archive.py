# ruff: noqa: E501 - migrations carry long SQL lines
"""Add the 'archive' operational status to membre.statut.

The member lifecycle needs a distinct ARCHIVED state (retired from current use, kept for
traceability, never physically deleted here), alongside actif / inactif / suspendu. The
existing CHECK constraint did not allow it, so the directory could not have an "Archivés"
compartment. This only widens the allowed set; no data change.

Revision ID: 0130_membre_statut_archive
Revises: 0129_technical_super_admin
Create Date: 2026-07-12
"""
from __future__ import annotations

from alembic import op

revision = "0130_membre_statut_archive"
down_revision = "0129_technical_super_admin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE membre DROP CONSTRAINT IF EXISTS membre_statut_chk")
    op.execute(
        "ALTER TABLE membre ADD CONSTRAINT membre_statut_chk "
        "CHECK (statut = ANY (ARRAY['actif'::text, 'inactif'::text, 'suspendu'::text, 'archive'::text]))"
    )


def downgrade() -> None:
    # Fold any archived member back to inactif before narrowing the constraint again.
    op.execute("UPDATE membre SET statut = 'inactif' WHERE statut = 'archive'")
    op.execute("ALTER TABLE membre DROP CONSTRAINT IF EXISTS membre_statut_chk")
    op.execute(
        "ALTER TABLE membre ADD CONSTRAINT membre_statut_chk "
        "CHECK (statut = ANY (ARRAY['actif'::text, 'inactif'::text, 'suspendu'::text]))"
    )
