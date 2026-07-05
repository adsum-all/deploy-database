# ruff: noqa: E501 - migrations carry long SQL and seeded text lines
"""Richer coordination/intendance and a direct member coordination axis.

Two independent structures of the same level, now with a real descriptive and
geographic identity (description, country by ISO code, continent, city, status)
instead of a bare name, and parity between the two. Adds a direct
``membre.coordination_id`` so a member can belong to a coordination OR an
intendance (mutually exclusive by CHECK), instead of only reaching a coordination
transitively through an intendance. Everything is additive and non-destructive:
existing rows keep their values, the text ``pays`` column is preserved next to
the new ISO ``pays_code``, and the exclusivity CHECK is trivially satisfied by
current members (which only ever carry ``intendance_id``).

Revision ID: 0066_coordination_intendance_enrichie
Revises: 0065_session_fin_geo
Create Date: 2026-07-05
"""
from __future__ import annotations

from alembic import op

revision = "0066_coordination_intendance_enrichie"
down_revision = "0065_session_fin_geo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Coordination: descriptive and geographic identity ------------------
    # description already exists (0007). Country is stored as an ISO 3166-1
    # alpha-2 code (source of truth), with the display name kept in the existing
    # free-text style for compatibility; continent and city complete the location.
    op.execute("ALTER TABLE coordination ADD COLUMN IF NOT EXISTS pays_code text")
    op.execute("ALTER TABLE coordination ADD COLUMN IF NOT EXISTS pays text")
    op.execute("ALTER TABLE coordination ADD COLUMN IF NOT EXISTS continent text")
    op.execute("ALTER TABLE coordination ADD COLUMN IF NOT EXISTS ville text")
    op.execute("ALTER TABLE coordination ADD COLUMN IF NOT EXISTS statut text NOT NULL DEFAULT 'actif'")

    # --- Intendance: parity with coordination -------------------------------
    # pays and ville already exist (0007); add description, ISO code, continent
    # and status so both structures reach the same level of detail.
    op.execute("ALTER TABLE intendance ADD COLUMN IF NOT EXISTS description text")
    op.execute("ALTER TABLE intendance ADD COLUMN IF NOT EXISTS pays_code text")
    op.execute("ALTER TABLE intendance ADD COLUMN IF NOT EXISTS continent text")
    op.execute("ALTER TABLE intendance ADD COLUMN IF NOT EXISTS statut text NOT NULL DEFAULT 'actif'")

    # --- Member: a direct coordination axis, exclusive with the intendance --
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS coordination_id uuid")
    op.execute("ALTER TABLE membre DROP CONSTRAINT IF EXISTS membre_coordination_fk")
    op.execute("ALTER TABLE membre ADD CONSTRAINT membre_coordination_fk FOREIGN KEY (coordination_id) REFERENCES coordination(id) ON DELETE SET NULL")
    op.execute("CREATE INDEX IF NOT EXISTS idx_membre_coordination ON membre(coordination_id)")
    # A member belongs to a coordination OR an intendance, not both (business
    # rule R3). Existing members only carry intendance_id, so this holds now.
    op.execute("ALTER TABLE membre DROP CONSTRAINT IF EXISTS membre_axe_orga_chk")
    op.execute("ALTER TABLE membre ADD CONSTRAINT membre_axe_orga_chk CHECK (coordination_id IS NULL OR intendance_id IS NULL)")


def downgrade() -> None:
    op.execute("ALTER TABLE membre DROP CONSTRAINT IF EXISTS membre_axe_orga_chk")
    op.execute("DROP INDEX IF EXISTS idx_membre_coordination")
    op.execute("ALTER TABLE membre DROP CONSTRAINT IF EXISTS membre_coordination_fk")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS coordination_id")

    op.execute("ALTER TABLE intendance DROP COLUMN IF EXISTS statut")
    op.execute("ALTER TABLE intendance DROP COLUMN IF EXISTS continent")
    op.execute("ALTER TABLE intendance DROP COLUMN IF EXISTS pays_code")
    op.execute("ALTER TABLE intendance DROP COLUMN IF EXISTS description")

    op.execute("ALTER TABLE coordination DROP COLUMN IF EXISTS statut")
    op.execute("ALTER TABLE coordination DROP COLUMN IF EXISTS ville")
    op.execute("ALTER TABLE coordination DROP COLUMN IF EXISTS continent")
    op.execute("ALTER TABLE coordination DROP COLUMN IF EXISTS pays")
    op.execute("ALTER TABLE coordination DROP COLUMN IF EXISTS pays_code")
