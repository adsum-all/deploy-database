"""Enrich the activity/event model with editorial content and human contributors,
so an activity can carry a rich description and its speakers, edited identically
from the back office and the collaboration app.

Additive only:
- ``description`` holds the rich text (a constrained HTML subset, sanitised server
  side before storage).
- ``intervenant_principal`` is the main speaker/author.
- ``intervenants`` is the list of secondary speakers.

Revision ID: 0102_evenement_desc_interv
Revises: 0101_collab_demande_notif
"""
from __future__ import annotations

from alembic import op

revision = "0102_evenement_desc_interv"
down_revision = "0101_collab_demande_notif"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE evenement ADD COLUMN IF NOT EXISTS description text")
    op.execute("ALTER TABLE evenement ADD COLUMN IF NOT EXISTS intervenant_principal text")
    op.execute("ALTER TABLE evenement ADD COLUMN IF NOT EXISTS intervenants text[] NOT NULL DEFAULT '{}'")


def downgrade() -> None:
    op.execute("ALTER TABLE evenement DROP COLUMN IF EXISTS intervenants")
    op.execute("ALTER TABLE evenement DROP COLUMN IF EXISTS intervenant_principal")
    op.execute("ALTER TABLE evenement DROP COLUMN IF EXISTS description")
