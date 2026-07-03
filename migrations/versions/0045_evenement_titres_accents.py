"""Fix missing French accents on seeded activity titles (display data).

Some example activities were seeded without diacritics ("Veillee", "Reunion",
"priere", "edition"). Notifications interpolate the raw title, so a member saw
"Reunion de la Commission Liturgie" instead of "Réunion". This corrects the data.

Revision ID: 0045_evenement_titres_accents
Revises: 0044_surveillance
Create Date: 2026-07-03
"""
from __future__ import annotations

from alembic import op

revision = "0045_evenement_titres_accents"
down_revision = "0044_surveillance"
branch_labels = None
depends_on = None

_FIX = [
    ("KAIROS 2026 - 16e edition", "KAIROS 2026 - 16e édition"),
    ("Veillee d'ouverture", "Veillée d'ouverture"),
    ("Veillee de priere", "Veillée de prière"),
    ("Reunion de la Commission Liturgie", "Réunion de la Commission Liturgie"),
]


def upgrade() -> None:
    for old, new in _FIX:
        op.execute("UPDATE evenement SET titre = %s WHERE titre = %s", (new, old))


def downgrade() -> None:
    for old, new in _FIX:
        op.execute("UPDATE evenement SET titre = %s WHERE titre = %s", (old, new))
