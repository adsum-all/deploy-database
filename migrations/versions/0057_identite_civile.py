# ruff: noqa: E501 - migrations carry long SQL lines
"""Structured civil identity, distinct from functions and pastoral appellations.

Adds on ``membre`` the fields needed to keep the civil identity clean and to stop
mixing it with functions or Berger/Bergere names:

- nom_naissance / nom_marital: a married woman's birth and marital names, so the
  single ``nom`` field no longer has to carry ambiguous cases.
- nom_affiche: which family name is the civil display name ('nom' default,
  'naissance' or 'marital'); the displayed civil name uses it.
- est_berger + nom_pastoral: whether the member is a Berger/Bergere and their
  pastoral name, shown in a dedicated zone, never in the civil title.
- fonction_perimetre: the scope of the function (commission, mission, ...), shown
  next to the function label, never in the civil title.

The displayed civil name (NOM Prenom1 [Prenom2]) is computed at read time by
app/identite.py, so no stored name is ever an endless title. This migration only
adds columns; it never drops or renames existing ones.

Revision ID: 0057_identite_civile
Revises: 0056_photo_focus
Create Date: 2026-07-04
"""
from __future__ import annotations

from alembic import op

revision = "0057_identite_civile"
down_revision = "0056_photo_focus"
branch_labels = None
depends_on = None

_COLUMNS = (
    "nom_naissance text",
    "nom_marital text",
    "nom_affiche text",
    "nom_pastoral text",
    "fonction_perimetre text",
)


def upgrade() -> None:
    for coldef in _COLUMNS:
        op.execute(f"ALTER TABLE membre ADD COLUMN IF NOT EXISTS {coldef}")
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS est_berger boolean NOT NULL DEFAULT false")
    op.execute("ALTER TABLE membre DROP CONSTRAINT IF EXISTS membre_nom_affiche_chk")
    op.execute(
        "ALTER TABLE membre ADD CONSTRAINT membre_nom_affiche_chk "
        "CHECK (nom_affiche IS NULL OR nom_affiche IN ('nom', 'naissance', 'marital')) NOT VALID"
    )
    # Bring existing family names to the display convention (uppercase). Given
    # names keep their stored value; their title case is applied at display time.
    op.execute("UPDATE membre SET nom = upper(nom) WHERE nom IS NOT NULL AND nom <> upper(nom)")


def downgrade() -> None:
    op.execute("ALTER TABLE membre DROP CONSTRAINT IF EXISTS membre_nom_affiche_chk")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS est_berger")
    for coldef in _COLUMNS:
        col = coldef.split(" ")[0]
        op.execute(f"ALTER TABLE membre DROP COLUMN IF EXISTS {col}")
