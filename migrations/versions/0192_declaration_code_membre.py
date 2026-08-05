# ruff: noqa: E501 - migrations carry long SQL lines
"""Tell apart a member who has no code from one who has not filled it in yet.

The member code is issued by the organisation, and normally everyone has one. Not
everyone does yet, so the form asks first whether they have one, and only then for
the code itself.

Without somewhere to write that answer, both cases look identical in the base: an
empty column. The organisation then cannot tell who to chase for a code they hold
from who is waiting to be given one, which is the only reason to ask the question at
all.

Three states on purpose. True says they have one, false says they declared they do
not, and null says nobody has been asked, which is where every member registered
before this stands. Defaulting to false would put words in their mouth.

Revision ID: 0192_declaration_code_membre
Revises: 0191_couleur_tribu
Create Date: 2026-08-02
"""
from __future__ import annotations

from alembic import op

revision = "0192_declaration_code_membre"
down_revision = "0191_couleur_tribu"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS a_code_membre boolean")
    op.execute(
        "COMMENT ON COLUMN membre.a_code_membre IS "
        "'Le membre déclare-t-il posséder un code délivré par l''organisation ? "
        "Vrai : il en a un. Faux : il a déclaré ne pas en avoir, et une demande de "
        "mise à jour lui sera ouverte le jour où il l''obtiendra. Null : la question "
        "ne lui a jamais été posée, ce qui est le cas de toute inscription antérieure.'"
    )

    # A member who already filled a code has answered the question by doing so, and
    # asking them again would be asking something the base already knows.
    op.execute(
        "UPDATE membre SET a_code_membre = true "
        "WHERE a_code_membre IS NULL AND code_membre IS NOT NULL AND btrim(code_membre) <> ''"
    )

    # The bulk unlock reads exactly this: validated members with no code and no
    # answer. Partial, so it stays small as the base grows and empties itself as
    # members are served.
    op.execute(
        "CREATE INDEX IF NOT EXISTS membre_code_membre_a_reclamer "
        "ON membre (statut_inscription) "
        "WHERE (code_membre IS NULL OR btrim(code_membre) = '') AND a_code_membre IS DISTINCT FROM false"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS membre_code_membre_a_reclamer")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS a_code_membre")
