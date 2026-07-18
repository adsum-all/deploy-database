# ruff: noqa: E501 - migrations carry long SQL lines
"""Notification center state: archiving and per-member hiding.

Adds the durable state a long-lived notification center needs: ``archive`` (moved
out of the active lists by the retention job, still auditable) and ``masque``
(hidden by the member from their own view, without destroying the institutional
record). A covering index keeps the paginated member feed fast over years of rows.

Revision ID: 0157_notification_centre
Revises: 0156_information_signature
Create Date: 2026-07-19
"""
from __future__ import annotations

from alembic import op

revision = "0157_notification_centre"
down_revision = "0156_information_signature"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE notification ADD COLUMN IF NOT EXISTS archive boolean NOT NULL DEFAULT false")
    op.execute("ALTER TABLE notification ADD COLUMN IF NOT EXISTS archive_le timestamptz")
    op.execute("ALTER TABLE notification ADD COLUMN IF NOT EXISTS masque boolean NOT NULL DEFAULT false")
    op.execute("ALTER TABLE notification ADD COLUMN IF NOT EXISTS masque_le timestamptz")
    # The member feed always filters by membre_id and orders by creation time desc.
    op.execute("CREATE INDEX IF NOT EXISTS ix_notification_membre_cree ON notification (membre_id, cree_le DESC)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_notification_membre_cree")
    op.execute("ALTER TABLE notification DROP COLUMN IF EXISTS masque_le")
    op.execute("ALTER TABLE notification DROP COLUMN IF EXISTS masque")
    op.execute("ALTER TABLE notification DROP COLUMN IF EXISTS archive_le")
    op.execute("ALTER TABLE notification DROP COLUMN IF EXISTS archive")
