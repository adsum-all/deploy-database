"""Make the coordination / intendance axis non-exclusive.

Migration 0066 introduced ``membre.coordination_id`` with a CHECK constraint
``membre_axe_orga_chk`` forbidding a member from carrying both a coordination
and an intendance at once. Field feedback: in rare cases a member legitimately
belongs to BOTH a coordination and an intendance, so this exclusivity is too
strict. This migration drops the exclusive CHECK. The registration form still
requires at least one of the two axes (application-level rule), and legacy
members that carry neither remain valid, so no data-level NOT NULL is added.

Revision ID: 0085_axe_orga_non_exclusif
Revises: 0084_evenement_annulation
"""
from __future__ import annotations

from alembic import op

revision = "0085_axe_orga_non_exclusif"
down_revision = "0084_evenement_annulation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Allow a member to belong to both a coordination and an intendance (rare
    # but legitimate). The FK on coordination_id and the index are kept.
    op.execute("ALTER TABLE membre DROP CONSTRAINT IF EXISTS membre_axe_orga_chk")


def downgrade() -> None:
    # Restore the exclusivity. Any member that now carries both axes would make
    # this fail, so it is only safe when such rows do not exist.
    op.execute(
        "ALTER TABLE membre ADD CONSTRAINT membre_axe_orga_chk "
        "CHECK (coordination_id IS NULL OR intendance_id IS NULL)"
    )
