# ruff: noqa: E501 - migrations carry long SQL and seeded text lines
"""Organisation taxonomy: commission type and optional self-hierarchies.

A structural unit under "Commission & mission" carries a type (commission,
mission or any other kind the administration adds later), so the same table
serves commissions and missions and a member can move freely between them by
changing a single link. Coordinations and intendances stay two independent
structures of the same level: neither requires the other. An optional parent on
each lets the administration build a coordination-over-coordination or
intendance-over-intendance hierarchy only when it is explicitly wanted, never by
default. No dependency is imposed.

Revision ID: 0061_org_type_parent
Revises: 0060_evenement_ciblage
Create Date: 2026-07-04
"""
from __future__ import annotations

from alembic import op

revision = "0061_org_type_parent"
down_revision = "0060_evenement_ciblage"
branch_labels = None
depends_on = None

# Seed units (nom without the type prefix; the prefix is derived from the type
# for display). Idempotent: only inserted when the name is not already present.
_UNITS = [
    ("SAINT GABRIEL", "commission"),
    ("EL GIBBOR", "mission"),
    ("CHOEUR KERUBIM", "commission"),
    ("EDEN", "commission"),
    ("VAILLANTS HEROS", "commission"),
    ("TIMOTHÉE", "mission"),
    ("TRIBU DE DAVID", "commission"),
    ("JEAN BAPTISTE", "mission"),
]


def upgrade() -> None:
    # Type of the unit: 'commission', 'mission', or any other kind added later.
    # Free text (lowercase slug) on purpose, so the administration can extend the
    # list from the interface without a schema change.
    op.execute("ALTER TABLE commission ADD COLUMN IF NOT EXISTS type_organisation text NOT NULL DEFAULT 'commission'")

    # Optional parent for a coordination-over-coordination hierarchy. Never
    # required; SET NULL on delete so removing a parent never deletes children.
    op.execute("ALTER TABLE coordination ADD COLUMN IF NOT EXISTS parent_id uuid")
    op.execute("ALTER TABLE coordination DROP CONSTRAINT IF EXISTS coordination_parent_fk")
    op.execute("ALTER TABLE coordination ADD CONSTRAINT coordination_parent_fk FOREIGN KEY (parent_id) REFERENCES coordination(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE coordination DROP CONSTRAINT IF EXISTS coordination_parent_not_self")
    op.execute("ALTER TABLE coordination ADD CONSTRAINT coordination_parent_not_self CHECK (parent_id IS NULL OR parent_id <> id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_coordination_parent ON coordination(parent_id)")

    # Optional parent for an intendance-over-intendance hierarchy, independent of
    # the equally optional coordination link (added in 0007).
    op.execute("ALTER TABLE intendance ADD COLUMN IF NOT EXISTS parent_id uuid")
    op.execute("ALTER TABLE intendance DROP CONSTRAINT IF EXISTS intendance_parent_fk")
    op.execute("ALTER TABLE intendance ADD CONSTRAINT intendance_parent_fk FOREIGN KEY (parent_id) REFERENCES intendance(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE intendance DROP CONSTRAINT IF EXISTS intendance_parent_not_self")
    op.execute("ALTER TABLE intendance ADD CONSTRAINT intendance_parent_not_self CHECK (parent_id IS NULL OR parent_id <> id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_intendance_parent ON intendance(parent_id)")

    for nom, type_org in _UNITS:
        op.execute(
            "INSERT INTO commission (nom, type_organisation) SELECT %s, %s "
            "WHERE NOT EXISTS (SELECT 1 FROM commission WHERE nom = %s)",
            (nom, type_org, nom),
        )


def downgrade() -> None:
    for nom, _type in _UNITS:
        op.execute("DELETE FROM commission WHERE nom = %s AND type_organisation IN ('commission', 'mission')", (nom,))
    op.execute("DROP INDEX IF EXISTS idx_intendance_parent")
    op.execute("ALTER TABLE intendance DROP CONSTRAINT IF EXISTS intendance_parent_not_self")
    op.execute("ALTER TABLE intendance DROP CONSTRAINT IF EXISTS intendance_parent_fk")
    op.execute("ALTER TABLE intendance DROP COLUMN IF EXISTS parent_id")
    op.execute("DROP INDEX IF EXISTS idx_coordination_parent")
    op.execute("ALTER TABLE coordination DROP CONSTRAINT IF EXISTS coordination_parent_not_self")
    op.execute("ALTER TABLE coordination DROP CONSTRAINT IF EXISTS coordination_parent_fk")
    op.execute("ALTER TABLE coordination DROP COLUMN IF EXISTS parent_id")
    op.execute("ALTER TABLE commission DROP COLUMN IF EXISTS type_organisation")
