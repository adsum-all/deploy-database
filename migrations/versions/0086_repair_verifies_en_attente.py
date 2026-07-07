"""Repair members verified by the administration but stuck in a pending state.

A member could be validated from the member sheet ("Valider l'identite", which
sets ``verifie = true``) instead of the inscription review queue (which sets
``statut_inscription = 'approuve'``). Such a member appeared VERIFIE + ACTIF in
the back office yet stayed blocked on the "inscription en cours d'examen" screen,
and lingered in the inscription review queue. The application code now keeps the
two paths consistent going forward (a verified identity also settles the
registration lifecycle). This migration heals the members already left in that
inconsistent state.

Idempotent: re-running matches no row once the data is consistent. Only members
already verified by the administration and still in a pending registration state
are advanced; dossiers still 'incomplet'/'modification_demandee' or 'refuse' are
never touched.

Revision ID: 0086_repair_verifies_en_attente
Revises: 0085_axe_orga_non_exclusif
"""
from __future__ import annotations

from alembic import op

revision = "0086_repair_verifies_en_attente"
down_revision = "0085_axe_orga_non_exclusif"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE membre "
        "SET statut_inscription = 'approuve', "
        "    motif_refus = NULL, "
        "    champs_a_corriger = NULL, "
        "    decision_le = COALESCE(decision_le, now()) "
        "WHERE verifie = true "
        "  AND statut_inscription IN ('soumis', 'en_revue')"
    )


def downgrade() -> None:
    # A data repair is not reversible: the prior per-member status is not stored.
    # No-op so the migration chain can still be stepped back structurally.
    pass
