"""Upgrade member requests to full enterprise tickets.

Adds to ``demande``: a human-readable sequential number (shown as DEM-000123),
category and subcategory (structured catalog), and a motivated closure
(motif_cloture, clos_le). Adds to ``demande_message``: an optional link to an
uploaded document so supporting files live inside the same ticket thread.
Existing rows are backfilled with a number and a category.

Revision ID: 0041_demande_ticket
Revises: 0040_document_chiffrement
Create Date: 2026-07-02
"""
from __future__ import annotations

from alembic import op

revision = "0041_demande_ticket"
down_revision = "0040_document_chiffrement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS demande_numero_seq")
    op.execute("ALTER TABLE demande ADD COLUMN IF NOT EXISTS numero bigint")
    op.execute("ALTER TABLE demande ALTER COLUMN numero SET DEFAULT nextval('demande_numero_seq')")
    op.execute("UPDATE demande SET numero = nextval('demande_numero_seq') WHERE numero IS NULL")
    op.execute("ALTER TABLE demande ADD COLUMN IF NOT EXISTS categorie text")
    op.execute("ALTER TABLE demande ADD COLUMN IF NOT EXISTS sous_categorie text")
    op.execute("ALTER TABLE demande ADD COLUMN IF NOT EXISTS motif_cloture text")
    op.execute("ALTER TABLE demande ADD COLUMN IF NOT EXISTS clos_le timestamptz")
    op.execute("UPDATE demande SET categorie = coalesce(categorie, type)")
    op.execute("ALTER TABLE demande_message ADD COLUMN IF NOT EXISTS document_id uuid")
    # Full ticket lifecycle states (controlled by the API state machine).
    op.execute("ALTER TABLE demande DROP CONSTRAINT IF EXISTS demande_statut_chk")
    op.execute(
        "ALTER TABLE demande ADD CONSTRAINT demande_statut_chk CHECK (statut IN "
        "('ouverte', 'en_cours', 'pieces_demandees', 'attente_membre', 'en_validation', 'resolue', 'refusee'))"
    )
    # Timeline entries are system-authored (status changes, document requests).
    op.execute("ALTER TABLE demande_message DROP CONSTRAINT IF EXISTS demande_message_auteur_chk")
    op.execute(
        "ALTER TABLE demande_message ADD CONSTRAINT demande_message_auteur_chk "
        "CHECK (auteur_type IN ('membre', 'staff', 'systeme'))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE demande_message DROP COLUMN IF EXISTS document_id")
    op.execute("ALTER TABLE demande DROP COLUMN IF EXISTS clos_le")
    op.execute("ALTER TABLE demande DROP COLUMN IF EXISTS motif_cloture")
    op.execute("ALTER TABLE demande DROP COLUMN IF EXISTS sous_categorie")
    op.execute("ALTER TABLE demande DROP COLUMN IF EXISTS categorie")
    op.execute("ALTER TABLE demande DROP COLUMN IF EXISTS numero")
    op.execute("DROP SEQUENCE IF EXISTS demande_numero_seq")
