"""Add the relational "cheminement" flag to the member.

A single or in-couple member (situation_matrimoniale in celibataire/en_couple) may
be "en cheminement": in a relationship progressing toward an eventual marriage. It
is an optional, self-declared boolean asked only for those two situations, kept
NULL otherwise (not asked / not applicable). It feeds community statistics on
members who are on that path; the identity of the other person is never collected.

This is distinct from ``cheminement_pastoral`` (the pastoral journey level) added
in 0007: this one is strictly about the marital/relational path.

Revision ID: 0153_membre_cheminement
Revises: 0152_organigramme_model
Create Date: 2026-07-18
"""
from __future__ import annotations

from alembic import op

revision = "0153_membre_cheminement"
down_revision = "0152_organigramme_model"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS en_cheminement boolean")


def downgrade() -> None:
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS en_cheminement")
