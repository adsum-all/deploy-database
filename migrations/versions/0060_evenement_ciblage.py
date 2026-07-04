# ruff: noqa: E501 - migrations carry long SQL and seeded text lines
"""Activity targeting: an event can be aimed at one organisational unit.

Until now every event appeared in every member's agenda. An event now carries a
target: ``general`` (everyone) or a single organisational unit (coordination,
commission, intendance or tribu). A member only sees a targeted event when it
matches the unit they belong to, so a coordination activity is no longer
broadcast to the whole community. ``mode`` is also constrained to the three
attendance modes (presentiel, en_ligne, hybride) so the value is reliable
everywhere it is displayed.

Revision ID: 0060_evenement_ciblage
Revises: 0059_membre_fonction_multi
Create Date: 2026-07-04
"""
from __future__ import annotations

from alembic import op

revision = "0060_evenement_ciblage"
down_revision = "0059_membre_fonction_multi"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Target of the event: 'general' means the whole community; any other value
    # pairs with cible_id, the id of the aimed organisational unit.
    op.execute("ALTER TABLE evenement ADD COLUMN IF NOT EXISTS cible_type text NOT NULL DEFAULT 'general'")
    op.execute("ALTER TABLE evenement DROP CONSTRAINT IF EXISTS evenement_cible_type_chk")
    op.execute(
        "ALTER TABLE evenement ADD CONSTRAINT evenement_cible_type_chk "
        "CHECK (cible_type IN ('general', 'coordination', 'commission', 'intendance', 'tribu'))"
    )
    op.execute("ALTER TABLE evenement ADD COLUMN IF NOT EXISTS cible_id uuid")
    # A general event carries no unit; a targeted event must name one. cible_id is
    # a soft polymorphic reference (coordination/commission/intendance/tribu), so
    # it is validated in the API against the chosen cible_type, not by a single FK.
    op.execute("ALTER TABLE evenement DROP CONSTRAINT IF EXISTS evenement_cible_pair_chk")
    op.execute(
        "ALTER TABLE evenement ADD CONSTRAINT evenement_cible_pair_chk "
        "CHECK ((cible_type = 'general' AND cible_id IS NULL) OR (cible_type <> 'general' AND cible_id IS NOT NULL))"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_evenement_cible ON evenement(cible_type, cible_id)")

    # Reliable attendance mode. Existing rows already use presentiel/hybride; NULL
    # stays allowed for legacy rows that never set it.
    op.execute("UPDATE evenement SET mode = 'en_ligne' WHERE mode IN ('en ligne', 'enligne', 'online', 'ligne', 'distanciel', 'distance')")
    op.execute("UPDATE evenement SET mode = 'presentiel' WHERE mode IN ('présentiel', 'presence', 'en presentiel')")
    op.execute("ALTER TABLE evenement DROP CONSTRAINT IF EXISTS evenement_mode_chk")
    op.execute(
        "ALTER TABLE evenement ADD CONSTRAINT evenement_mode_chk "
        "CHECK (mode IS NULL OR mode IN ('presentiel', 'en_ligne', 'hybride'))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE evenement DROP CONSTRAINT IF EXISTS evenement_mode_chk")
    op.execute("DROP INDEX IF EXISTS idx_evenement_cible")
    op.execute("ALTER TABLE evenement DROP CONSTRAINT IF EXISTS evenement_cible_pair_chk")
    op.execute("ALTER TABLE evenement DROP CONSTRAINT IF EXISTS evenement_cible_type_chk")
    op.execute("ALTER TABLE evenement DROP COLUMN IF EXISTS cible_id")
    op.execute("ALTER TABLE evenement DROP COLUMN IF EXISTS cible_type")
