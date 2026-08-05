# ruff: noqa: E501 - migrations carry long SQL lines
"""Give each tribe its colour, as a setting rather than a constant.

A tribe is recognised by its colour before it is read by its name: members know
which one is theirs by sight. The platform knew only the name, so every tribe looked
the same everywhere it appeared, and the one piece of information a member uses to
find themselves in a list was missing from it.

The colour lives on the row, next to the name, for the same reason the name does:
another organisation deploying this product has its own groups, or none at all, and
a palette written into the code would be this organisation's palette in everybody
else's application. Seeded here for the tribes that exist, editable afterwards from
the back office, and empty for a tribe created later until somebody chooses.

Seeding matches on the name with accents and case folded away: this base holds
SIMEON with an accent and NEPHTALI with its letters in an order the printed chart
does not use, and an exact comparison would silently colour neither.

Revision ID: 0191_couleur_tribu
Revises: 0190_appareil_push
Create Date: 2026-08-02
"""
from __future__ import annotations

from alembic import op

revision = "0191_couleur_tribu"
down_revision = "0190_appareil_push"
branch_labels = None
depends_on = None

#: The twelve tribes and the colour each one is known by. Keys are compared with
#: accents and case removed, so a stored "SIMÉON" matches the "SIMEON" written here.
_COULEURS = {
    "RUBEN": "#1e6fd9",      # bleu
    "SIMEON": "#e8a0a8",     # rose clair
    "LEVI": "#ffffff",       # blanc
    "JUDA": "#7b4a2d",       # brun
    "DAN": "#1e7a33",        # vert
    "NEPHTALI": "#c99a16",   # jaune foncé
    "GAD": "#f07a18",        # orange
    "ASHER": "#a8a8a8",      # gris
    "ISSACAR": "#e8232a",    # rouge
    "ZABULON": "#f2e31c",    # jaune
    "JOSEPH": "#a34f72",     # rose foncé
    "BENJAMIN": "#e85ac8",   # magenta
}


def upgrade() -> None:
    op.execute("ALTER TABLE tribu ADD COLUMN IF NOT EXISTS couleur text")
    # Refused at the door rather than at the screen: a value that is not a colour
    # would land straight inside a style attribute on every page showing the tribe.
    op.execute(
        "ALTER TABLE tribu DROP CONSTRAINT IF EXISTS tribu_couleur_hexadecimale"
    )
    op.execute(
        "ALTER TABLE tribu ADD CONSTRAINT tribu_couleur_hexadecimale "
        "CHECK (couleur IS NULL OR couleur ~ '^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')"
    )
    op.execute(
        "COMMENT ON COLUMN tribu.couleur IS "
        "'Couleur de la tribu, hexadécimal. Réglable par l''organisation : une autre "
        "organisation a ses propres groupes, ou n''en a pas. Vide tant que personne "
        "n''a choisi, auquel cas l''interface n''affiche aucune pastille.'"
    )

    # Seed only what is still empty, so re-running this never overwrites a colour an
    # administrator has since chosen.
    #
    # Accents are folded with translate() rather than with unaccent(): that function
    # comes from an extension this database does not necessarily carry, and a
    # migration that depends on one is a migration that fails on a fresh deployment.
    # The names here are ASCII and uppercase, so the comparison is exact once the
    # stored name has been folded the same way.
    pliage = "upper(translate(nom, 'ÉÈÊËéèêëÀÂÁàâáÎÏîïÔÖÓôöóÙÛÜùûüÇç', 'EEEEEEEEAAAAAAIIIIOOOOOOUUUUUUCC'))"
    for nom, couleur in _COULEURS.items():
        op.execute(
            f"UPDATE tribu SET couleur = '{couleur}' "
            f"WHERE couleur IS NULL AND {pliage} = '{nom}'"
        )


def downgrade() -> None:
    op.execute("ALTER TABLE tribu DROP CONSTRAINT IF EXISTS tribu_couleur_hexadecimale")
    op.execute("ALTER TABLE tribu DROP COLUMN IF EXISTS couleur")
