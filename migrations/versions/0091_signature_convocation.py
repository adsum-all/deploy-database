"""Seed the missing signature settings and add a convocation signature.

The global ``signature`` and ``site_officiel`` settings were referenced by the
code and the admin help but never seeded, so the admin could not edit them (the
PUT returned 404) and the global signature stayed the hard-coded default. This
seeds them. It also adds a dedicated ``signature_convocation`` family so the
attendance survey ("sondage de pointage") and the just-starting reminders can be
signed by a specific authority (default "Le Modérateur"), configurable by the
administration. All inserts are idempotent (ON CONFLICT DO NOTHING), so an
already-configured value is never overwritten.

Revision ID: 0091_signature_convocation
Revises: 0090_ciblage_enrichi
"""
from __future__ import annotations

from alembic import op

revision = "0091_signature_convocation"
down_revision = "0090_ciblage_enrichi"
branch_labels = None
depends_on = None

# cle -> default value (empty means "editable but unset")
_SEED = {
    "signature": "Sacerdoce Royal",
    "site_officiel": "",
    "signature_convocation": "Le Modérateur",
}


def upgrade() -> None:
    for cle, valeur in _SEED.items():
        op.execute(
            "INSERT INTO integration_config (cle, valeur, categorie) "
            f"VALUES ('{cle}', {'NULL' if valeur == '' else repr(valeur)}, 'signature') "
            "ON CONFLICT (cle) DO NOTHING"
        )


def downgrade() -> None:
    op.execute("DELETE FROM integration_config WHERE cle = 'signature_convocation'")
