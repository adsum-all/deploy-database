# ruff: noqa: E501 - migrations carry long SQL lines
"""Perimeter-scoped access groups: give a group membership an organisational scope.

A membership in an access group can now be GLOBAL (whole base) or SCOPED to one
organisational unit (a coordination, an intendance, a commission/mission, or a
tribu). A scoped membership grants a bounded pilotage access to that unit only,
never a global back-office access, so a coordination responsable never sees the
members of another coordination. A person may hold several scoped memberships
(the same group over several perimeters), hence the widened uniqueness.

``portee_id`` is a soft polymorphic reference (it points to coordination /
intendance / commission / tribu depending on ``portee_type``), validated at the
application layer; no single foreign key can express it, so none is added and the
schema counters are unchanged.

Revision ID: 0071_membre_groupe_portee
Revises: 0070_utilisateur_membre_uq
Create Date: 2026-07-05
"""
from __future__ import annotations

from alembic import op

revision = "0071_membre_groupe_portee"
down_revision = "0070_utilisateur_membre_uq"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE membre_groupe ADD COLUMN IF NOT EXISTS portee_type text NOT NULL DEFAULT 'global'")
    op.execute("ALTER TABLE membre_groupe ADD COLUMN IF NOT EXISTS portee_id uuid")
    op.execute("ALTER TABLE membre_groupe DROP CONSTRAINT IF EXISTS membre_groupe_portee_chk")
    op.execute(
        "ALTER TABLE membre_groupe ADD CONSTRAINT membre_groupe_portee_chk CHECK ("
        "(portee_type = 'global' AND portee_id IS NULL) OR "
        "(portee_type IN ('coordination', 'intendance', 'commission', 'tribu') AND portee_id IS NOT NULL))"
    )
    # A member may hold the same group over several perimeters, so uniqueness is on
    # (member, group, scope). NULL portee_id (global) is folded to a sentinel so a
    # global membership stays unique per group.
    op.execute("ALTER TABLE membre_groupe DROP CONSTRAINT IF EXISTS membre_groupe_uniq")
    op.execute("DROP INDEX IF EXISTS membre_groupe_scope_uniq")
    op.execute(
        "CREATE UNIQUE INDEX membre_groupe_scope_uniq ON membre_groupe "
        "(membre_id, groupe_id, portee_type, coalesce(portee_id, '00000000-0000-0000-0000-000000000000'::uuid))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS membre_groupe_scope_uniq")
    op.execute("ALTER TABLE membre_groupe DROP CONSTRAINT IF EXISTS membre_groupe_portee_chk")
    op.execute("ALTER TABLE membre_groupe ADD CONSTRAINT membre_groupe_uniq UNIQUE (membre_id, groupe_id)")
    op.execute("ALTER TABLE membre_groupe DROP COLUMN IF EXISTS portee_type")
    op.execute("ALTER TABLE membre_groupe DROP COLUMN IF EXISTS portee_id")
