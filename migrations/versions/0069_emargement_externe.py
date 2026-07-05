# ruff: noqa: E501 - migrations carry long SQL lines
"""External lightweight check-in: opt-in flag per event.

The external attendance link lets a person confirm their presence from a public
page without logging in, by identifying with their country dial code, phone
number and last name. That surface is opened deny-by-default: it works only for
an event whose organizer explicitly enabled ``emargement_externe`` and only
inside the attendance window. No new table is added; the external channel writes
into the existing ``participation`` table (unique per event and member), so a
person is still counted exactly once across every channel.

Revision ID: 0069_emargement_externe
Revises: 0068_groupes_acces
Create Date: 2026-07-05
"""
from __future__ import annotations

from alembic import op

revision = "0069_emargement_externe"
down_revision = "0068_groupes_acces"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE evenement ADD COLUMN IF NOT EXISTS emargement_externe boolean NOT NULL DEFAULT false")


def downgrade() -> None:
    op.execute("ALTER TABLE evenement DROP COLUMN IF EXISTS emargement_externe")
