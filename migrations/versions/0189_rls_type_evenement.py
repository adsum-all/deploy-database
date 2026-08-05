# ruff: noqa: E501 - migrations carry long SQL lines
"""Put row level security on type_evenement, the last table without it.

The Constitution requires row level security on every table. After 0188 a count over
the rendered schema gave 142 tables and 141 with the feature enabled; this is the
one that remained.

It is the catalogue of activity kinds and the colour each one is drawn in. Every
signed-in role reads it, because a calendar cannot be rendered without it, so the
read policy is deliberately open to any authenticated role rather than to a list:
restricting it further would blank the calendar for whoever was left out, and the
catalogue holds no personal data at all.

Writing is another matter. Renaming or deleting a kind changes how every past and
future activity is labelled across every application, so it stays with the roles that
administer the organisation's reference data.

Revision ID: 0189_rls_type_evenement
Revises: 0188_rls_registre_email
Create Date: 2026-08-02
"""
from __future__ import annotations

from alembic import op

revision = "0189_rls_type_evenement"
down_revision = "0188_rls_registre_email"
branch_labels = None
depends_on = None

#: Who may change the catalogue. Reading is open to any authenticated role.
_ECRITURE = "ARRAY['super_admin', 'admin', 'gestionnaire']::text[]"


def upgrade() -> None:
    op.execute("ALTER TABLE type_evenement ENABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS type_evenement_lecture ON type_evenement")
    # adsum_current_role() returns NULL when nothing was set, which is what an
    # unauthenticated connection looks like. Written through COALESCE rather than
    # relying on a NULL comparison evaluating to false: the rule then says what it
    # means, instead of working by a property of three-valued logic that the next
    # person to read it has to know.
    op.execute(
        "CREATE POLICY type_evenement_lecture ON type_evenement FOR SELECT "
        "USING (COALESCE(adsum_current_role(), '') <> '')"
    )

    op.execute("DROP POLICY IF EXISTS type_evenement_ecriture ON type_evenement")
    op.execute(
        f"CREATE POLICY type_evenement_ecriture ON type_evenement FOR ALL "
        f"USING (COALESCE(adsum_current_role(), '') = ANY({_ECRITURE})) "
        f"WITH CHECK (COALESCE(adsum_current_role(), '') = ANY({_ECRITURE}))"
    )

    op.execute(
        "COMMENT ON POLICY type_evenement_lecture ON type_evenement IS "
        "'Catalogue des genres d''activité et de leurs couleurs. Lisible par tout rôle "
        "authentifié : sans lui aucun calendrier ne peut s''afficher, et la table ne "
        "contient aucune donnée personnelle.'"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS type_evenement_lecture ON type_evenement")
    op.execute("DROP POLICY IF EXISTS type_evenement_ecriture ON type_evenement")
    op.execute("ALTER TABLE type_evenement DISABLE ROW LEVEL SECURITY")
