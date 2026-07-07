# ruff: noqa: E501 - migrations carry long SQL lines
"""Single canonical matricule format ADS-{L1}{L2}-{NNNNNN}-{X}, all members migrated.

Replaces the coexisting historical formats (ADS-NNNNNN and ADS-YYYY-NNNNNN) by one
format for 100% of members. A global sequence gives a unique 6-digit part, the two
letters are the family-name and first-given-name initials (accent-stripped, 'X' when
missing), and a random trailing letter is a readability differentiator. The former
matricule is preserved in ``matricule_historique`` and a CHECK constraint locks the
format going forward. Data regeneration runs online only (skipped in --sql).

Revision ID: 0081_matricule_format_unique
Revises: 0080_code_membre
Create Date: 2026-07-06
"""
from __future__ import annotations

import random
import string
import unicodedata

from alembic import context, op

revision = "0081_matricule_format_unique"
down_revision = "0080_code_membre"
branch_labels = None
depends_on = None

_FMT = r"^ADS-[A-Z]{2}-[0-9]{6}-[A-Z]$"


def _premiere_lettre(valeur: str | None) -> str:
    ascii_form = unicodedata.normalize("NFD", valeur or "").encode("ascii", "ignore").decode()
    for ch in ascii_form:
        if ch.isalpha():
            return ch.upper()
    return "X"


def _initiales(nom: str | None, prenoms: str | None) -> str:
    premier = (prenoms or "").strip().split(" ", 1)[0]
    return _premiere_lettre(nom) + _premiere_lettre(premier)


def upgrade() -> None:
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS matricule_historique text")
    op.execute("CREATE SEQUENCE IF NOT EXISTS matricule_seq")

    if not context.is_offline_mode():
        bind = op.get_bind()
        rows = list(bind.exec_driver_sql("SELECT id, matricule, nom, prenoms FROM membre ORDER BY matricule"))
        seq = 0
        for mid, ancien, nom, prenoms in rows:
            # Skip a member already in the canonical format (idempotent re-run).
            if ancien and __import__("re").fullmatch(_FMT, ancien):
                continue
            seq += 1
            nouveau = f"ADS-{_initiales(nom, prenoms)}-{seq:06d}-{random.choice(string.ascii_uppercase)}"
            bind.exec_driver_sql(
                "UPDATE membre SET matricule = %s, matricule_historique = COALESCE(matricule_historique, %s) WHERE id = %s",
                (nouveau, ancien, mid),
            )
        # Position the sequence past the last assigned number so new members continue it.
        bind.exec_driver_sql("SELECT setval('matricule_seq', GREATEST(%s, (SELECT last_value FROM matricule_seq)))", (max(seq, 1),))

    # Lock the single format going forward (all rows now conform).
    op.execute("ALTER TABLE membre DROP CONSTRAINT IF EXISTS membre_matricule_format_chk")
    op.execute(f"ALTER TABLE membre ADD CONSTRAINT membre_matricule_format_chk CHECK (matricule ~ '{_FMT}')")


def downgrade() -> None:
    op.execute("ALTER TABLE membre DROP CONSTRAINT IF EXISTS membre_matricule_format_chk")
    # Restore the historical matricule where kept.
    if not context.is_offline_mode():
        op.get_bind().exec_driver_sql("UPDATE membre SET matricule = matricule_historique WHERE matricule_historique IS NOT NULL")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS matricule_historique")
    op.execute("DROP SEQUENCE IF EXISTS matricule_seq")
