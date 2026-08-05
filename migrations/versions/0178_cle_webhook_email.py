# ruff: noqa: E501 - migrations carry long SQL lines
"""Declare the shared secret that authenticates the mail provider's callbacks.

The delivery webhook is the only way the platform learns that a message bounced.
Left unauthenticated it would accept fabricated events from anyone, which would let
a stranger mark real deliveries as failures, or failures as deliveries. The provider
cannot send a custom header, so the secret travels in the callback URL and therefore
has to be long, single-purpose and rotatable from the integrations screen.

The row is created empty on purpose: a value written into a migration would be the
same on every environment and would sit in the repository forever.

Revision ID: 0178_cle_webhook_email
Revises: 0177_reprise_historique_envois
Create Date: 2026-07-28
"""
from __future__ import annotations

from alembic import op

revision = "0178_cle_webhook_email"
down_revision = "0177_reprise_historique_envois"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO integration_config (cle, valeur, categorie)
        VALUES ('email_webhook_secret', NULL, 'email')
        ON CONFLICT (cle) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM integration_config WHERE cle = 'email_webhook_secret'")
