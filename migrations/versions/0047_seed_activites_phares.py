# ruff: noqa: E501 - migrations carry long SQL and seeded text lines
"""Seed the flagship, fraternity-wide example activities (curated, limited set).

The catalog of example events lacked the organization's signature gatherings that
the business explicitly recognizes (a 21-day fast, Revelation, the annual congress,
the ministry school). This adds them as a small, coherent, professional set at the
fraternity scale (no sub-commission tracking), with correct French accents and
example dates in the near future (now() + interval), inserted idempotently so a
re-run never duplicates a title.

Revision ID: 0047_seed_activites_phares
Revises: 0046_notif_catalogue_complet
Create Date: 2026-07-03
"""
from __future__ import annotations

from alembic import op

revision = "0047_seed_activites_phares"
down_revision = "0046_notif_catalogue_complet"
branch_labels = None
depends_on = None

# (titre, type, volet, mode, debut_interval, fin_interval, lieu)
# Fraternity-wide flagship activities only. Titles carry correct accents.
_EVENTS = [
    ("21 jours de jeûne et de prière", "jeune", "A", "hybride", "14 days", "35 days", "Siège Sacerdoce Royal, Abidjan"),
    ("Révélation", "rassemblement", "B", "presentiel", "45 days", "45 days 06:00:00", "Palais de la culture, Abidjan"),
    ("Congrès annuel du Sacerdoce Royal", "congres", "B", "presentiel", "60 days", "62 days", "Palais de la culture, Abidjan"),
    ("École de ministère", "formation", "A", "hybride", "17 days", "17 days 03:00:00", "Salle Saint-Gabriel, Abidjan"),
]


def upgrade() -> None:
    for titre, type_, volet, mode, debut, fin, lieu in _EVENTS:
        op.execute(
            "INSERT INTO evenement (titre, type, volet, mode, debut, fin, lieu) "
            "SELECT %s, %s, %s, %s, now() + %s::interval, now() + %s::interval, %s "
            "WHERE NOT EXISTS (SELECT 1 FROM evenement WHERE titre = %s)",
            (titre, type_, volet, mode, debut, fin, lieu, titre),
        )


def downgrade() -> None:
    for titre, *_ in _EVENTS:
        op.execute("DELETE FROM evenement WHERE titre = %s", (titre,))
