"""Collaboration card enrichment: priority, complexity, number, start date, and
the label / assignee / checklist domains, ported from the Lovable prototype.

Additive only (ADD COLUMN, CREATE TABLE): existing collab tables, data and the
other applications are untouched. Every new table gets row level security with
the same committee read/write policy as the base collaboration tables.

Revision ID: 0096_collab_carte_enrichie
Revises: 0095_appareil_confiance_rls
"""
from __future__ import annotations

from alembic import op

revision = "0096_collab_carte_enrichie"
down_revision = "0095_appareil_confiance_rls"
branch_labels = None
depends_on = None

COMITE = "ARRAY['super_admin', 'admin', 'gestionnaire']::text[]"
LECTURE = "ARRAY['super_admin', 'admin', 'gestionnaire', 'direction']::text[]"

NEW_TABLES = (
    "collab_etiquette",
    "collab_carte_etiquette",
    "collab_carte_membre",
    "collab_checklist",
    "collab_checklist_item",
)


def upgrade() -> None:
    # 1) Enrich the card with the prototype's own fields (additive columns).
    op.execute("ALTER TABLE collab_carte ADD COLUMN IF NOT EXISTS priorite text NOT NULL DEFAULT 'normale'")
    op.execute("ALTER TABLE collab_carte ADD COLUMN IF NOT EXISTS complexite integer")
    op.execute("ALTER TABLE collab_carte ADD COLUMN IF NOT EXISTS numero integer")
    op.execute("ALTER TABLE collab_carte ADD COLUMN IF NOT EXISTS debut timestamptz")
    op.execute("ALTER TABLE collab_carte ADD COLUMN IF NOT EXISTS archive boolean NOT NULL DEFAULT false")
    # Monotone per-board card number counter, so a number is never reused after a
    # deletion (the prototype reused numbers, which the server now prevents).
    op.execute("ALTER TABLE collab_tableau ADD COLUMN IF NOT EXISTS compteur_cartes integer NOT NULL DEFAULT 0")

    # 2) Labels: defined at the board level, reused across its cards.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collab_etiquette (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tableau_id uuid NOT NULL REFERENCES collab_tableau(id) ON DELETE CASCADE,
            nom text NOT NULL,
            couleur text NOT NULL DEFAULT '#2A4FAD',
            par_defaut boolean NOT NULL DEFAULT false,
            position integer NOT NULL DEFAULT 0
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collab_carte_etiquette (
            carte_id uuid NOT NULL REFERENCES collab_carte(id) ON DELETE CASCADE,
            etiquette_id uuid NOT NULL REFERENCES collab_etiquette(id) ON DELETE CASCADE,
            PRIMARY KEY (carte_id, etiquette_id)
        )
        """
    )

    # 3) Assignees and followers of a card (role tells them apart).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collab_carte_membre (
            carte_id uuid NOT NULL REFERENCES collab_carte(id) ON DELETE CASCADE,
            membre_id uuid NOT NULL REFERENCES membre(id) ON DELETE CASCADE,
            role text NOT NULL DEFAULT 'assigne',
            PRIMARY KEY (carte_id, membre_id, role)
        )
        """
    )

    # 4) Checklists and their items.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collab_checklist (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            carte_id uuid NOT NULL REFERENCES collab_carte(id) ON DELETE CASCADE,
            titre text NOT NULL DEFAULT 'Checklist',
            position integer NOT NULL DEFAULT 0
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collab_checklist_item (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            checklist_id uuid NOT NULL REFERENCES collab_checklist(id) ON DELETE CASCADE,
            texte text NOT NULL,
            fait boolean NOT NULL DEFAULT false,
            assigne_id uuid REFERENCES membre(id) ON DELETE SET NULL,
            echeance timestamptz,
            position integer NOT NULL DEFAULT 0
        )
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS idx_collab_etiquette_tableau ON collab_etiquette(tableau_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_collab_carte_etiquette_carte ON collab_carte_etiquette(carte_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_collab_carte_membre_carte ON collab_carte_membre(carte_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_collab_checklist_carte ON collab_checklist(carte_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_collab_checklist_item_liste ON collab_checklist_item(checklist_id)")

    for table in NEW_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_select ON {table} FOR SELECT "
            f"USING (adsum_current_role() = ANY({LECTURE}))"
        )
        op.execute(
            f"CREATE POLICY {table}_write ON {table} FOR ALL "
            f"USING (adsum_current_role() = ANY({COMITE})) "
            f"WITH CHECK (adsum_current_role() = ANY({COMITE}))"
        )


def downgrade() -> None:
    for table in NEW_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_select ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_write ON {table}")
    op.execute("DROP TABLE IF EXISTS collab_checklist_item CASCADE")
    op.execute("DROP TABLE IF EXISTS collab_checklist CASCADE")
    op.execute("DROP TABLE IF EXISTS collab_carte_membre CASCADE")
    op.execute("DROP TABLE IF EXISTS collab_carte_etiquette CASCADE")
    op.execute("DROP TABLE IF EXISTS collab_etiquette CASCADE")
    op.execute("ALTER TABLE collab_tableau DROP COLUMN IF EXISTS compteur_cartes")
    op.execute("ALTER TABLE collab_carte DROP COLUMN IF EXISTS archive")
    op.execute("ALTER TABLE collab_carte DROP COLUMN IF EXISTS debut")
    op.execute("ALTER TABLE collab_carte DROP COLUMN IF EXISTS numero")
    op.execute("ALTER TABLE collab_carte DROP COLUMN IF EXISTS complexite")
    op.execute("ALTER TABLE collab_carte DROP COLUMN IF EXISTS priorite")
