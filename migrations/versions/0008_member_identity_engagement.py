"""Add the tribe, engagement, marital and sacrament fields to the member.

Adds a ``tribu`` table (the twelve tribes of Israel, each with its patriarch) and
links the member to it. Adds, on ``membre``: type_membre (engagement level),
promotion, situation_matrimoniale and type_mariage (required marital information),
and optional profession, niveau_etudes and the catholic sacraments (baptise,
confirme, premiere_communion). Foreign key, index and RLS are set consistently
with the existing schema (ADR-0002).

Revision ID: 0008_member_identity_engagement
Revises: 0007_member_fields_org
Create Date: 2026-06-29
"""
from __future__ import annotations

from alembic import op

revision = "0008_member_identity_engagement"
down_revision = "0007_member_fields_org"
branch_labels = None
depends_on = None

TYPE_MEMBRE = (
    "membre_simple",
    "nouveau_engage",
    "aspirant",
    "engage",
    "berger",
    "responsable",
)
SITUATION = ("celibataire", "en_couple", "fiance", "marie", "veuf", "divorce")
MARIAGE = ("dot", "religieux", "dot_et_religieux", "civil")


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE tribu (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            nom text UNIQUE NOT NULL,
            patriarche text,
            description text,
            cree_le timestamptz DEFAULT now()
        )
        """
    )

    type_chk = ", ".join(f"'{v}'" for v in TYPE_MEMBRE)
    situ_chk = ", ".join(f"'{v}'" for v in SITUATION)
    mariage_chk = ", ".join(f"'{v}'" for v in MARIAGE)
    op.execute(
        f"""
        ALTER TABLE membre
            ADD COLUMN tribu_id uuid,
            ADD COLUMN type_membre text NOT NULL DEFAULT 'membre_simple',
            ADD COLUMN promotion text,
            ADD COLUMN situation_matrimoniale text,
            ADD COLUMN type_mariage text,
            ADD COLUMN profession text,
            ADD COLUMN niveau_etudes text,
            ADD COLUMN baptise boolean,
            ADD COLUMN confirme boolean,
            ADD COLUMN premiere_communion boolean,
            ADD CONSTRAINT membre_type_membre_chk CHECK (type_membre IN ({type_chk})),
            ADD CONSTRAINT membre_situation_chk
                CHECK (situation_matrimoniale IS NULL OR situation_matrimoniale IN ({situ_chk})),
            ADD CONSTRAINT membre_mariage_chk
                CHECK (type_mariage IS NULL OR type_mariage IN ({mariage_chk}))
        """
    )
    op.execute(
        "ALTER TABLE membre ADD CONSTRAINT membre_tribu_fk "
        "FOREIGN KEY (tribu_id) REFERENCES tribu(id) ON DELETE SET NULL"
    )
    op.execute("CREATE INDEX idx_membre_tribu ON membre(tribu_id)")

    op.execute("ALTER TABLE tribu ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tribu_select ON tribu FOR SELECT "
        "USING (adsum_current_role() = ANY("
        "ARRAY['super_admin', 'admin', 'gestionnaire', 'controleur', 'direction']::text[]))"
    )
    op.execute(
        "CREATE POLICY tribu_write ON tribu FOR ALL "
        "USING (adsum_current_role() = ANY(ARRAY['super_admin', 'admin']::text[])) "
        "WITH CHECK (adsum_current_role() = ANY(ARRAY['super_admin', 'admin']::text[]))"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tribu_select ON tribu")
    op.execute("DROP POLICY IF EXISTS tribu_write ON tribu")
    op.execute("DROP INDEX IF EXISTS idx_membre_tribu")
    op.execute("ALTER TABLE membre DROP CONSTRAINT IF EXISTS membre_tribu_fk")
    op.execute(
        """
        ALTER TABLE membre
            DROP CONSTRAINT IF EXISTS membre_type_membre_chk,
            DROP CONSTRAINT IF EXISTS membre_situation_chk,
            DROP CONSTRAINT IF EXISTS membre_mariage_chk,
            DROP COLUMN IF EXISTS tribu_id,
            DROP COLUMN IF EXISTS type_membre,
            DROP COLUMN IF EXISTS promotion,
            DROP COLUMN IF EXISTS situation_matrimoniale,
            DROP COLUMN IF EXISTS type_mariage,
            DROP COLUMN IF EXISTS profession,
            DROP COLUMN IF EXISTS niveau_etudes,
            DROP COLUMN IF EXISTS baptise,
            DROP COLUMN IF EXISTS confirme,
            DROP COLUMN IF EXISTS premiere_communion
        """
    )
    op.execute("DROP TABLE IF EXISTS tribu CASCADE")
