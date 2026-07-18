# ruff: noqa: E501 - migrations carry long SQL lines
"""Attribution catalogue: explicit four-category discriminator.

The ``fonction_honorifique`` catalogue historically mixed four distinct concepts
under one flat table, which leaked into the admin UI, the registration form,
notifications and birthday displays:

- TITRE (``titre``): a consecration name. Default: Berger/Bergere. Reflected by
  the administration-granted ``membre.est_berger`` flag and ``nom_pastoral``.
- FONCTION SPECIALE (``fonction_speciale``): exceptional top-level governance
  (Fondateur, Moderateur, Berger des missions).
- FONCTION (``fonction``): ordinary operational/hierarchical role (Intendant,
  Coordinateur, Responsable, Sous-responsable, Intendant/Controleur general).
- FONCTION PARTICULIERE (``fonction_particuliere``): transversal role parallel to
  the main hierarchy (Patriarche and future aides).

This migration is ADDITIVE and backward compatible. It adds an explicit
``categorie`` discriminator (CHECK-constrained), an optional ``abreviation`` for
compact displays, a ``niveau_hierarchique`` and a ``transversal`` flag, then
back-fills every existing catalogue key to its correct category. No row is
deleted; abbreviations are set only for ordinary/particular functions (titles and
special functions always render in full).

Revision ID: 0149_categorie_attribution
Revises: 0148_declaration_berger
Create Date: 2026-07-18
"""
from __future__ import annotations

from alembic import op

revision = "0149_categorie_attribution"
down_revision = "0148_declaration_berger"
branch_labels = None
depends_on = None

_CATEGORIES = ("titre", "fonction_speciale", "fonction", "fonction_particuliere")

# Reclassification of every catalogue key. Covers both the live prod catalogue
# (curated by the admin: controleur_general/intendant_general/sous_responsable
# added, bsg/bsg_missions removed) AND the historical seed of 0026/0092 (which
# still creates bsg/bsg_missions on a fresh database). Each UPDATE is a no-op on
# rows that do not exist, so the set stays correct for prod and for fresh DBs.
_RECLASS = {
    "berger": "titre",
    "fondateur": "fonction_speciale",
    "moderateur": "fonction_speciale",
    "berger_missions": "fonction_speciale",
    "bsg": "fonction_speciale",
    "bsg_missions": "fonction_speciale",
    "controleur_general": "fonction",
    "intendant_general": "fonction",
    "coordinateur": "fonction",
    "intendant": "fonction",
    "responsable": "fonction",
    "sous_responsable": "fonction",
    "patriarche": "fonction_particuliere",
}

# Compact-display abbreviations for ordinary/particular functions only.
_ABBREV = {
    "controleur_general": "Contr. gen.",
    "intendant_general": "Int. gen.",
    "coordinateur": "Coord.",
    "intendant": "Int.",
    "responsable": "Resp.",
    "sous_responsable": "Sous-resp.",
}


def upgrade() -> None:
    op.execute("ALTER TABLE fonction_honorifique ADD COLUMN IF NOT EXISTS categorie text NOT NULL DEFAULT 'fonction'")
    op.execute("ALTER TABLE fonction_honorifique ADD COLUMN IF NOT EXISTS abreviation text")
    op.execute("ALTER TABLE fonction_honorifique ADD COLUMN IF NOT EXISTS niveau_hierarchique integer")
    op.execute("ALTER TABLE fonction_honorifique ADD COLUMN IF NOT EXISTS transversal boolean NOT NULL DEFAULT false")

    # Back-fill the category before locking the CHECK, so pre-existing rows pass.
    for cle, categorie in _RECLASS.items():
        op.execute(
            f"UPDATE fonction_honorifique SET categorie = '{categorie}' WHERE cle = '{cle}'"
        )
    # Transversal flag mirrors the particular-function category (Patriarche & co).
    op.execute("UPDATE fonction_honorifique SET transversal = true WHERE categorie = 'fonction_particuliere'")

    for cle, abrege in _ABBREV.items():
        op.execute(
            f"UPDATE fonction_honorifique SET abreviation = '{abrege}' WHERE cle = '{cle}' AND abreviation IS NULL"
        )

    valeurs = ", ".join(f"'{c}'" for c in _CATEGORIES)
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fonction_honorifique_categorie_check') THEN "
        f"ALTER TABLE fonction_honorifique ADD CONSTRAINT fonction_honorifique_categorie_check CHECK (categorie IN ({valeurs})); "
        "END IF; END $$;"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_fonction_honorifique_categorie ON fonction_honorifique (categorie, actif)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_fonction_honorifique_categorie")
    op.execute("ALTER TABLE fonction_honorifique DROP CONSTRAINT IF EXISTS fonction_honorifique_categorie_check")
    op.execute("ALTER TABLE fonction_honorifique DROP COLUMN IF EXISTS transversal")
    op.execute("ALTER TABLE fonction_honorifique DROP COLUMN IF EXISTS niveau_hierarchique")
    op.execute("ALTER TABLE fonction_honorifique DROP COLUMN IF EXISTS abreviation")
    op.execute("ALTER TABLE fonction_honorifique DROP COLUMN IF EXISTS categorie")
