# ruff: noqa: E501 - migrations carry long SQL lines
"""Shepherd self-declaration at registration (to be confirmed by the administration).

Members joining the platform often already ARE shepherds (bergers/bergeres) in the
community. Until now the registration form had no way to say so: ``est_berger`` is
an administration-granted consecration flag and must stay so. This migration adds
the DECLARATION side of the workflow:

- ``berger_declare``: the member declares being a shepherd during registration.
  It never grants anything by itself; the administration reviews the dossier and,
  if appropriate, grants the real ``est_berger`` consecration flag.
- ``berger_nom_declare``: the shepherd name the member wishes to appear under
  (optional). The administration remains the sole authority on ``nom_pastoral``.

Revision ID: 0148_declaration_berger
Revises: 0147_referentiel_cibles_activite
Create Date: 2026-07-18
"""
from __future__ import annotations

from alembic import op

revision = "0148_declaration_berger"
down_revision = "0147_referentiel_cibles_activite"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS berger_declare boolean NOT NULL DEFAULT false")
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS berger_nom_declare text")


def downgrade() -> None:
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS berger_nom_declare")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS berger_declare")
