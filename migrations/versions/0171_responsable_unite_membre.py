# ruff: noqa: E501 - migrations carry long SQL lines
"""Point the organisational responsible of a unit at a MEMBER, not at an account.

The responsible of an intendance, a coordination or a sub-commission is a person of
the organisation. The schema referenced ``utilisateur`` (the application account)
for those three tables, while ``commission.responsable_id`` and
``tribu.patriarche_membre_id`` already referenced ``membre``. That inconsistency is
the schema-level form of the confusion this platform must never make: holding a
function is not the same thing as holding an application account. A person can lead
an intendance without ever logging in, and an account can exist without any office.

Practical consequence before this migration: the chart builder resolved holders in
the ``membre`` table using ``utilisateur`` identifiers, so the responsible of an
intendance or a coordination could never be resolved and every such post was
rendered as vacant.

Existing values are converted through ``utilisateur.membre_id``; a value that cannot
be resolved to a real member is cleared rather than kept dangling.

Revision ID: 0171_responsable_unite_membre
Revises: 0170_groupes_standard_doc
Create Date: 2026-07-24
"""
from __future__ import annotations

from alembic import op

revision = "0171_responsable_unite_membre"
down_revision = "0170_groupes_standard_doc"
branch_labels = None
depends_on = None

# table -> constraint name currently pointing at utilisateur(id)
_TABLES = {
    "intendance": "intendance_responsable_fk",
    "coordination": "coordination_responsable_fk",
    "sous_commission": "sous_commission_responsable_fk",
}


def upgrade() -> None:
    for table, contrainte in _TABLES.items():
        # 1. Drop the old constraint first: while it still points at utilisateur, any
        #    attempt to store a member identifier would violate it.
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {contrainte}")
        # 2. Convert account identifiers into member identifiers.
        op.execute(
            f"UPDATE {table} t SET responsable_id = u.membre_id "
            f"FROM utilisateur u WHERE u.id = t.responsable_id AND u.membre_id IS NOT NULL"
        )
        # 3. Clear anything that still does not designate an existing member, so the
        #    new constraint can be created and nothing is left pointing nowhere.
        op.execute(
            f"UPDATE {table} t SET responsable_id = NULL WHERE t.responsable_id IS NOT NULL "
            f"AND NOT EXISTS (SELECT 1 FROM membre m WHERE m.id = t.responsable_id)"
        )
        # 4. Point the foreign key at membre.
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT {contrainte} "
            f"FOREIGN KEY (responsable_id) REFERENCES membre(id) ON DELETE SET NULL"
        )


def downgrade() -> None:
    # The reverse conversion would have to guess an account for each member and would
    # lose the responsibles that have no account at all, so the previous references
    # are not restored: only the constraint target is put back.
    for table, contrainte in _TABLES.items():
        op.execute(f"UPDATE {table} SET responsable_id = NULL WHERE responsable_id IS NOT NULL")
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {contrainte}")
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT {contrainte} "
            f"FOREIGN KEY (responsable_id) REFERENCES utilisateur(id) ON DELETE SET NULL"
        )
