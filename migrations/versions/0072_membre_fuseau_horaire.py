# ruff: noqa: E501 - migrations carry long SQL lines
"""Store each member's IANA time zone so server-rendered times are localized.

Activity start/end are already stored as absolute instants (``timestamptz``), so
the member apps display them in the browser's local zone automatically. But
server-rendered messages (Telegram, e-mail, survey notifications) have no browser
to rely on: they need the member's own zone to show, for example, an activity at
12:00 UTC as 14:00 for a member in Europe/Paris. This column holds the standard
IANA identifier (e.g. ``Europe/Paris``, ``Africa/Abidjan``) detected from the
member's device, never a fixed offset, so seasonal changes are handled correctly.

Revision ID: 0072_membre_fuseau_horaire
Revises: 0071_membre_groupe_portee
Create Date: 2026-07-05
"""
from __future__ import annotations

from alembic import op

revision = "0072_membre_fuseau_horaire"
down_revision = "0071_membre_groupe_portee"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS fuseau_horaire text")


def downgrade() -> None:
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS fuseau_horaire")
