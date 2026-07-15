"""Third decision outcome for duplicate detections: request more documents.

The administration previously had only two outcomes on a flagged pair: confirm
it is a duplicate, or dismiss it. Real triage needs a middle ground: neither
member's file is conclusive, so a registration manager asks the person for an
identity document before deciding. This adds the 'documents_demandes' status and
a free-text 'note' so the reason (which document, why) is recorded and audited.

Revision ID: 0118_doublon_documents
Revises: 0117_collab_sous_espace
Create Date: 2026-07-11
"""
from __future__ import annotations

from alembic import op

revision = "0118_doublon_documents"
down_revision = "0117_collab_sous_espace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Widen the status check to allow the new triage outcome. The inline column
    # check created in 0018 is auto-named detection_doublon_statut_check.
    op.execute("ALTER TABLE detection_doublon DROP CONSTRAINT IF EXISTS detection_doublon_statut_check")
    op.execute(
        """
        ALTER TABLE detection_doublon
        ADD CONSTRAINT detection_doublon_statut_check
        CHECK (statut IN ('nouveau', 'confirme', 'ignore', 'documents_demandes'))
        """
    )
    # Free-text justification of the decision (which document is requested, why a
    # pair was confirmed or set apart). Nullable: older rows have no note.
    op.execute("ALTER TABLE detection_doublon ADD COLUMN IF NOT EXISTS note text")


def downgrade() -> None:
    op.execute("ALTER TABLE detection_doublon DROP COLUMN IF EXISTS note")
    op.execute("ALTER TABLE detection_doublon DROP CONSTRAINT IF EXISTS detection_doublon_statut_check")
    op.execute(
        """
        ALTER TABLE detection_doublon
        ADD CONSTRAINT detection_doublon_statut_check
        CHECK (statut IN ('nouveau', 'confirme', 'ignore'))
        """
    )
