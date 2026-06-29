"""Extend the member profile and add the organizational hierarchy.

Adds, on ``membre``: genre, date_naissance, pays, ville, intendance_id (the
geographic structure), berger_referent_id (the referring shepherd), date_entree,
cheminement_pastoral (pastoral journey) and statut_administratif (computed-like).

Adds three organizational tables matching the community structure: coordination,
intendance (belongs to a coordination, located in a country) and sous_commission
(belongs to a commission). Foreign keys, indexes and per-role RLS policies are set
consistently with the existing schema (ADR-0002).

Revision ID: 0007_member_fields_org
Revises: 0006_audit_actor_relation
Create Date: 2026-06-29
"""
from __future__ import annotations

from alembic import op

revision = "0007_member_fields_org"
down_revision = "0006_audit_actor_relation"
branch_labels = None
depends_on = None

CHEMINEMENT = (
    "nouveau",
    "en_accompagnement",
    "membre_actif",
    "responsable",
    "a_relancer",
    "en_pause",
    "ancien_membre",
)

NEW_TABLES = ("coordination", "intendance", "sous_commission")


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE coordination (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            nom text NOT NULL,
            description text,
            responsable_id uuid,
            cree_le timestamptz DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE intendance (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            nom text NOT NULL,
            pays text,
            ville text,
            coordination_id uuid,
            responsable_id uuid,
            cree_le timestamptz DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE sous_commission (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            nom text NOT NULL,
            commission_id uuid,
            responsable_id uuid,
            cree_le timestamptz DEFAULT now()
        )
        """
    )

    chk = ", ".join(f"'{c}'" for c in CHEMINEMENT)
    op.execute(
        f"""
        ALTER TABLE membre
            ADD COLUMN genre text,
            ADD COLUMN date_naissance date,
            ADD COLUMN pays text,
            ADD COLUMN ville text,
            ADD COLUMN intendance_id uuid,
            ADD COLUMN berger_referent_id uuid,
            ADD COLUMN date_entree date,
            ADD COLUMN cheminement_pastoral text NOT NULL DEFAULT 'nouveau',
            ADD COLUMN statut_administratif text NOT NULL DEFAULT 'nouveau',
            ADD CONSTRAINT membre_genre_chk CHECK (genre IS NULL OR genre IN ('homme', 'femme', 'autre')),
            ADD CONSTRAINT membre_cheminement_chk CHECK (cheminement_pastoral IN ({chk}))
        """
    )

    foreign_keys = [
        ("intendance", "intendance_coordination_fk", "coordination_id", "coordination"),
        ("intendance", "intendance_responsable_fk", "responsable_id", "utilisateur"),
        ("coordination", "coordination_responsable_fk", "responsable_id", "utilisateur"),
        ("sous_commission", "sous_commission_commission_fk", "commission_id", "commission"),
        ("sous_commission", "sous_commission_responsable_fk", "responsable_id", "utilisateur"),
        ("membre", "membre_intendance_fk", "intendance_id", "intendance"),
        ("membre", "membre_berger_fk", "berger_referent_id", "utilisateur"),
    ]
    for table, name, column, ref in foreign_keys:
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT {name} "
            f"FOREIGN KEY ({column}) REFERENCES {ref}(id) ON DELETE SET NULL"
        )

    op.execute("CREATE INDEX idx_membre_intendance ON membre(intendance_id)")
    op.execute("CREATE INDEX idx_membre_berger ON membre(berger_referent_id)")
    op.execute("CREATE INDEX idx_intendance_coordination ON intendance(coordination_id)")
    op.execute("CREATE INDEX idx_sous_commission_commission ON sous_commission(commission_id)")

    select_roles = "ARRAY['super_admin', 'admin', 'gestionnaire', 'controleur', 'direction']::text[]"
    write_roles = "ARRAY['super_admin', 'admin']::text[]"
    for table in NEW_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_select ON {table} FOR SELECT "
            f"USING (adsum_current_role() = ANY({select_roles}))"
        )
        op.execute(
            f"CREATE POLICY {table}_write ON {table} FOR ALL "
            f"USING (adsum_current_role() = ANY({write_roles})) "
            f"WITH CHECK (adsum_current_role() = ANY({write_roles}))"
        )


def downgrade() -> None:
    for table in NEW_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_select ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_write ON {table}")
    op.execute("DROP INDEX IF EXISTS idx_membre_intendance")
    op.execute("DROP INDEX IF EXISTS idx_membre_berger")
    op.execute("DROP INDEX IF EXISTS idx_intendance_coordination")
    op.execute("DROP INDEX IF EXISTS idx_sous_commission_commission")
    op.execute("ALTER TABLE membre DROP CONSTRAINT IF EXISTS membre_intendance_fk")
    op.execute("ALTER TABLE membre DROP CONSTRAINT IF EXISTS membre_berger_fk")
    op.execute(
        """
        ALTER TABLE membre
            DROP CONSTRAINT IF EXISTS membre_genre_chk,
            DROP CONSTRAINT IF EXISTS membre_cheminement_chk,
            DROP COLUMN IF EXISTS genre,
            DROP COLUMN IF EXISTS date_naissance,
            DROP COLUMN IF EXISTS pays,
            DROP COLUMN IF EXISTS ville,
            DROP COLUMN IF EXISTS intendance_id,
            DROP COLUMN IF EXISTS berger_referent_id,
            DROP COLUMN IF EXISTS date_entree,
            DROP COLUMN IF EXISTS cheminement_pastoral,
            DROP COLUMN IF EXISTS statut_administratif
        """
    )
    for table in ("sous_commission", "intendance", "coordination"):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
