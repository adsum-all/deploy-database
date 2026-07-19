# ruff: noqa: E501 - migrations carry long SQL lines
"""Header-banner opt-in flag on an Information.

``affiche_entete`` controls whether an Information is surfaced in the member app
header banner (the highlighted band above the member card) in addition to the
feed. Strictly off by default so nothing is promoted to the header unless an
administrator explicitly ticks the box, keeping that placement for the few
communications no member should miss.

Revision ID: 0161_information_affiche_entete
Revises: 0160_institutionnel
Create Date: 2026-07-19
"""
from __future__ import annotations

from alembic import op

revision = "0161_information_affiche_entete"
down_revision = "0160_institutionnel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE information ADD COLUMN IF NOT EXISTS affiche_entete boolean NOT NULL DEFAULT false")


def downgrade() -> None:
    op.execute("ALTER TABLE information DROP COLUMN IF EXISTS affiche_entete")
