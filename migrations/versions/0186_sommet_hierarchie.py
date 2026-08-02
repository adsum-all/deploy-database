# ruff: noqa: E501 - migrations carry long SQL lines
"""Say in the data which functions sit at the top of the organisation.

The upward chain a member sees ends with five function keys written into the code:
intendant general, controleur general, berger missions, moderateur, fondateur. Vacant
ones are still displayed, as "Poste a pourvoir". For any other organisation that is
five invented levels above their own leadership, and nothing in the interface can
remove them.

The information already exists in the data as niveau_hierarchique, but nothing said
where the units stop and the leadership begins. This column says it, and it is seeded
from exactly the five keys the code used, so the chain every member sees today is
unchanged.

Revision ID: 0186_sommet_hierarchie
Revises: 0185_vocabulaire_org
Create Date: 2026-07-31
"""
from __future__ import annotations

from alembic import op

revision = "0186_sommet_hierarchie"
down_revision = "0185_vocabulaire_org"
branch_labels = None
depends_on = None

# The apex as the code held it, lowest authority first. Seeded so nothing moves.
_SOMMET = ("intendant_general", "controleur_general", "berger_missions", "moderateur", "fondateur")


def upgrade() -> None:
    op.execute(
        "ALTER TABLE fonction_honorifique ADD COLUMN IF NOT EXISTS est_sommet boolean NOT NULL DEFAULT false"
    )
    op.execute(
        "COMMENT ON COLUMN fonction_honorifique.est_sommet IS "
        "'Cette fonction fait partie du sommet de l''organisation : elle apparaît dans la chaîne "
        "hiérarchique de chaque membre, au-dessus de ses propres unités, même si le poste est vacant.'"
    )
    # Inlined rather than bound so the migration also renders under
    # `alembic upgrade --sql`: driver binding needs a live connection, and offline
    # mode has none. The keys are the module constant above, never anything outside.
    cles = ", ".join("'" + c.replace("'", "''") + "'" for c in _SOMMET)
    op.execute(f"UPDATE fonction_honorifique SET est_sommet = true WHERE cle IN ({cles})")
    # The chain is read by ordering on the level, so a top function without one would
    # land in an arbitrary place. Only those that carry a level can be apex.
    op.execute(
        "UPDATE fonction_honorifique SET est_sommet = false WHERE niveau_hierarchique IS NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS fonction_honorifique_sommet_idx "
        "ON fonction_honorifique (niveau_hierarchique DESC) WHERE est_sommet = true"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS fonction_honorifique_sommet_idx")
    op.execute("ALTER TABLE fonction_honorifique DROP COLUMN IF EXISTS est_sommet")
