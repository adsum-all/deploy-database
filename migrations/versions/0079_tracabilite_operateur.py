# ruff: noqa: E501 - migrations carry long SQL lines
"""Operator traceability: record who created a presence and who wrote a staff message.

Additive, nullable columns so existing rows are untouched. ``presence.cree_par`` and
``demande_message.auteur_id`` reference the acting account, closing the audit gap where
a check-in or a staff reply carried no operator identity.

Revision ID: 0079_tracabilite_operateur
Revises: 0078_invitation_engagement
Create Date: 2026-07-06
"""
from __future__ import annotations

from alembic import op

revision = "0079_tracabilite_operateur"
down_revision = "0078_invitation_engagement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE presence ADD COLUMN IF NOT EXISTS cree_par uuid REFERENCES utilisateur(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE demande_message ADD COLUMN IF NOT EXISTS auteur_id uuid REFERENCES utilisateur(id) ON DELETE SET NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE demande_message DROP COLUMN IF EXISTS auteur_id")
    op.execute("ALTER TABLE presence DROP COLUMN IF EXISTS cree_par")
