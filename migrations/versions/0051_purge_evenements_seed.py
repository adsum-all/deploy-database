"""Remove the seeded example events from production (no fake data, ever).

Example events had been seeded into the production database (insertion-time
signature 23:03, plus one 00:43 row from migration 0047). The daily J-1
reminder then notified real members about an event that never existed
("Rencontre du dimanche", 12 notifications on 2026-07-03), causing real harm.

This deletes the proven seed batch only: exact title AND the seed insertion
time signature, so an admin-created event with the same title and a real
schedule is never touched. Seed-origin titles that the administration later
re-dated by hand (21 jours de jeune, Ecole de ministere, Congres annuel) are
considered adopted as real and are kept. Fictitious child rows (presence,
participation, QR tokens) of the deleted events are removed with them.

Example events belong in the dev seed (deployment/database/seed/real_data.py)
only, never in a migration: 0047's event seeding was a mistake, corrected here.

Revision ID: 0051_purge_evenements_seed
Revises: 0050_integrite_fk
Create Date: 2026-07-03
"""
from __future__ import annotations

from alembic import op

revision = "0051_purge_evenements_seed"
down_revision = "0050_integrite_fk"
branch_labels = None
depends_on = None

# (titre exact, signature horaire d'insertion du seed)
_FAKE = [
    ("Office du matin", "23:03"),
    ("Rencontre du dimanche", "23:03"),
    ("Exposition du Saint Sacrement", "23:03"),
    ("Veillée de prière", "23:03"),
    ("Formation - Les fondements de la foi", "23:03"),
    ("Renouvellement de l'engagement annuel", "23:03"),
    ("KAIROS 2026 - 16e édition", "23:03"),
    ("Révélation", "00:43"),
]

_CHILDREN = ("participation", "presence", "comptage_volet_b", "questionnaire")


def _detacher_collab() -> None:
    """Collaboration cards may reference an event: detach, never delete work."""
    for titre, heure in _FAKE:
        op.execute(
            "UPDATE collab_carte SET evenement_id = NULL WHERE evenement_id IN "
            "(SELECT id FROM evenement WHERE titre = %s AND to_char(debut, 'HH24:MI') = %s)",
            (titre, heure),
        )


def upgrade() -> None:
    _detacher_collab()
    for titre, heure in _FAKE:
        for child in _CHILDREN:
            op.execute(
                f"DELETE FROM {child} WHERE evenement_id IN "
                "(SELECT id FROM evenement WHERE titre = %s AND to_char(debut, 'HH24:MI') = %s)",
                (titre, heure),
            )
        op.execute(
            "DELETE FROM evenement WHERE titre = %s AND to_char(debut, 'HH24:MI') = %s",
            (titre, heure),
        )


def downgrade() -> None:
    # Deliberately irreversible: fake data must not come back.
    pass
