"""Enrich the honorific-function taxonomy with a family and a hierarchical level.

Until now ``fonction_honorifique`` only had a boolean ``est_vip`` plus a display
``ordre``. That is too poor to let a member filter people by category. This adds:

- ``famille``: a coherent grouping usable as a filter (direction, coordination,
  bergers, patriarches, responsables).
- ``niveau``: a hierarchical rank (lower = higher authority), distinct from the
  display ``ordre`` and from ``niveau_engagement`` (which is about type_membre).

The ten seeded functions are backfilled into families and levels. ``famille`` is
nullable so any orphan/custom key stays valid, and ``est_vip``/``ordre`` are kept
untouched, so nothing that relied on them changes.

Revision ID: 0092_fonction_famille_niveau
Revises: 0091_signature_convocation
"""
from __future__ import annotations

from alembic import op

revision = "0092_fonction_famille_niveau"
down_revision = "0091_signature_convocation"
branch_labels = None
depends_on = None

# famille -> (clés de fonction, niveau hierarchique)
_FAMILLES = {
    "direction": (("fondateur", "moderateur", "bsg_missions", "bsg"), 10),
    "coordination": (("coordinateur", "intendant"), 30),
    "patriarches": (("patriarche",), 40),
    "bergers": (("berger", "berger_missions"), 50),
    "responsables": (("responsable",), 70),
}


def upgrade() -> None:
    op.execute("ALTER TABLE fonction_honorifique ADD COLUMN IF NOT EXISTS famille text")
    op.execute("ALTER TABLE fonction_honorifique ADD COLUMN IF NOT EXISTS niveau integer NOT NULL DEFAULT 100")
    for famille, (cles, niveau) in _FAMILLES.items():
        liste = ", ".join(f"'{c}'" for c in cles)
        op.execute(f"UPDATE fonction_honorifique SET famille = '{famille}', niveau = {niveau} WHERE cle IN ({liste})")


def downgrade() -> None:
    op.execute("ALTER TABLE fonction_honorifique DROP COLUMN IF EXISTS niveau")
    op.execute("ALTER TABLE fonction_honorifique DROP COLUMN IF EXISTS famille")
