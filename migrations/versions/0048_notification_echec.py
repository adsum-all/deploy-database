"""Delivery-failure observability: a log of failed notification channel sends.

Until now a channel send that failed (e-mail rejected, Telegram unreachable,
WhatsApp error) was best-effort and silently dropped, so the administration had
no way to see that a member never received a message. This adds a compact ledger
of failed deliveries (one row per failed channel attempt) that the back office
lists, so failures are observable and can be followed up. Successful and in-app
deliveries are not recorded here (they never fail meaningfully), keeping the
table small.

Revision ID: 0048_notification_echec
Revises: 0047_seed_activites_phares
Create Date: 2026-07-03
"""
from __future__ import annotations

from alembic import op

revision = "0048_notification_echec"
down_revision = "0047_seed_activites_phares"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_echec (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            membre_id uuid,
            type_cle text,
            canal text NOT NULL,
            detail text,
            resolu boolean NOT NULL DEFAULT false,
            cree_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_notification_echec_recent ON notification_echec (cree_le DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_notification_echec_ouvert ON notification_echec (resolu, cree_le DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS notification_echec")
