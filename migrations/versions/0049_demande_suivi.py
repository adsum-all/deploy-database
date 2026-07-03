"""Request tracking: record who took charge and when, and attestation follow-up.

The ticket system had a full state machine but never recorded the take-over
(who handles the request, since when), so neither the member nor the staff
could see whether a request was actually being handled. The hand-signed
attestation flow lacked a submission timestamp and a rejection reason, so the
member card could not show "transmitted on ..." nor why a scan was rejected.

Revision ID: 0049_demande_suivi
Revises: 0048_notification_echec
Create Date: 2026-07-03
"""
from __future__ import annotations

from alembic import op

revision = "0049_demande_suivi"
down_revision = "0048_notification_echec"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE demande ADD COLUMN IF NOT EXISTS pris_en_charge_par uuid")
    op.execute("ALTER TABLE demande ADD COLUMN IF NOT EXISTS pris_en_charge_le timestamptz")
    op.execute("ALTER TABLE attestation_manuelle ADD COLUMN IF NOT EXISTS soumise_le timestamptz")
    op.execute("ALTER TABLE attestation_manuelle ADD COLUMN IF NOT EXISTS motif_rejet text")
    # Backfill: a request already beyond 'ouverte' has necessarily been handled;
    # date the take-over at the first staff/system activity we know (maj_le).
    op.execute(
        "UPDATE demande SET pris_en_charge_le = coalesce(pris_en_charge_le, maj_le) "
        "WHERE statut <> 'ouverte' AND pris_en_charge_le IS NULL"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE demande DROP COLUMN IF EXISTS pris_en_charge_par")
    op.execute("ALTER TABLE demande DROP COLUMN IF EXISTS pris_en_charge_le")
    op.execute("ALTER TABLE attestation_manuelle DROP COLUMN IF EXISTS soumise_le")
    op.execute("ALTER TABLE attestation_manuelle DROP COLUMN IF EXISTS motif_rejet")
