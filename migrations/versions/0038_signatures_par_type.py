"""Per-category message signatures, admin-configurable.

Until now every notification was signed with a single global signature. The
business wants a distinct sign-off per message family (birthday, informational,
acknowledgement, approval, correction, reminder). These rows make each signature
settable from the admin integration settings; an empty value falls back to the
global ``signature`` (itself defaulting to "Sacerdoce Royal").

Revision ID: 0038_signatures_par_type
Revises: 0037_telegram_cleanup
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0038_signatures_par_type"
down_revision = "0037_telegram_cleanup"
branch_labels = None
depends_on = None

_KEYS = [
    "signature_anniversaire",
    "signature_information",
    "signature_accuse",
    "signature_approbation",
    "signature_correction",
    "signature_rappel",
]


def upgrade() -> None:
    for cle in _KEYS:
        op.execute(
            "INSERT INTO integration_config (cle, valeur, categorie) VALUES (%s, NULL, 'signature') "
            "ON CONFLICT (cle) DO NOTHING",
            (cle,),
        )


def downgrade() -> None:
    for cle in _KEYS:
        op.execute("DELETE FROM integration_config WHERE cle = %s", (cle,))
