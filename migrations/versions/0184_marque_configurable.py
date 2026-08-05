# ruff: noqa: E501 - migrations carry long SQL lines
"""Declare the branding an organisation can change about the messages it sends.

The name in the e-mail header, the palette and the footer line were literals. That was
true enough while one organisation used the platform. It stops being true the moment a
second one does: a parish deploying this would send its members mail headed ADSUM,
signed Sacerdoce Royal, and footed with an address in Abidjan.

The rows are created EMPTY. The code falls back to exactly what was written there
before, so applying this changes nothing about the messages going out today. It only
makes them changeable, which is the whole point: a platform meant to be deployed for
organisations nobody has met yet cannot decide how they present themselves.

Revision ID: 0184_marque_configurable
Revises: 0183_session_et_fenetres
Create Date: 2026-07-31
"""
from __future__ import annotations

from alembic import op

revision = "0184_marque_configurable"
down_revision = "0183_session_et_fenetres"
branch_labels = None
depends_on = None

_CLES = (
    "org_marque",
    "org_couleur_principale",
    "org_couleur_sombre",
    "org_baseline",
)


def _lit(v: str) -> str:
    """A SQL string literal, quotes doubled."""
    return "'" + v.replace("'", "''") + "'"


def upgrade() -> None:
    # One multi-row statement rather than a loop: the pooled connection reuses
    # prepared statement names, and a loop collides on them. Values inlined rather
    # than bound so the migration also renders under `alembic upgrade --sql`: driver
    # binding needs a live connection, and offline mode has none. They are the module
    # constants above, never anything from outside.
    valeurs = ", ".join(f"({_lit(c)}, NULL, 'organisation')" for c in _CLES)
    op.execute(
        f"INSERT INTO integration_config (cle, valeur, categorie) VALUES {valeurs} "
        "ON CONFLICT (cle) DO NOTHING"
    )


def downgrade() -> None:
    cles = ", ".join(_lit(c) for c in _CLES)
    op.execute(f"DELETE FROM integration_config WHERE cle IN ({cles})")
