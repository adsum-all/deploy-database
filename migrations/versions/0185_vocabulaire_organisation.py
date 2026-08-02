# ruff: noqa: E501 - migrations carry long SQL lines
"""Let an organisation name its own units and responsibilities.

The platform speaks of coordinations, intendances, commissions, tribus, bergers and
patriarches. Those words belong to one organisation. A parish speaks of secteurs and
services, a prayer group of cellules and responsables, a school of promotions and
referents. Handed this application as it stands, any of them has to adopt somebody
else's vocabulary to use their own tools.

The tables keep their names: renaming a schema in production buys nothing and risks
everything. What becomes changeable is what people read on screen.

Three facets per term, because French needs all three to build a correct sentence:
a singular, a plural, and the article that precedes it. "la tribu", "les tribus",
"l'intendance": an interface that only stores the singular writes "le intendance".

The rows are created EMPTY and the code falls back to the words in use today, so
applying this changes nothing for the organisation running now.

Revision ID: 0185_vocabulaire_organisation
Revises: 0184_marque_configurable
Create Date: 2026-07-31
"""
from __future__ import annotations

from alembic import op

revision = "0185_vocabulaire_org"
down_revision = "0184_marque_configurable"
branch_labels = None
depends_on = None

_TERMES = ("coordination", "intendance", "commission", "tribu", "berger", "patriarche", "membre")
_FACETTES = ("singulier", "pluriel", "article")


def _cles() -> list[str]:
    return [f"org_mot_{t}_{f}" for t in _TERMES for f in _FACETTES]


def _lit(v: str) -> str:
    """A SQL string literal, quotes doubled."""
    return "'" + v.replace("'", "''") + "'"


def upgrade() -> None:
    # One multi-row statement rather than a loop: the pooled connection reuses
    # prepared statement names, and a loop collides on them. Values inlined rather
    # than bound so the migration also renders under `alembic upgrade --sql`: driver
    # binding needs a live connection, and offline mode has none. The keys are built
    # from the module constants above, never from anything outside.
    valeurs = ", ".join(f"({_lit(c)}, NULL, 'organisation')" for c in _cles())
    op.execute(
        f"INSERT INTO integration_config (cle, valeur, categorie) VALUES {valeurs} "
        "ON CONFLICT (cle) DO NOTHING"
    )


def downgrade() -> None:
    cles = ", ".join(_lit(c) for c in _cles())
    op.execute(f"DELETE FROM integration_config WHERE cle IN ({cles})")
