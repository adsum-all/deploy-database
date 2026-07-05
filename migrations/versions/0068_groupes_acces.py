# ruff: noqa: E501 - migrations carry long SQL and seeded text lines
"""Access groups (RBAC): decouple platform access from the member identity.

Everyone is first a MEMBER with their own account, whose default role is
'membre'. Platform access (back-office, direction, pilotage) is NOT the member's
identity: it is granted only by adding the member to an access group. A group
carries the platform role it grants; a member's effective role is the highest
role granted by their active groups, or 'membre' when they belong to none.
Removing a member from every group reverts the account to 'membre' WITHOUT
deleting it, so the member never loses access to their own member account.

This migration only adds the tables and seeds the built-in groups; the backend
keeps the account role in sync with the groups.

Revision ID: 0068_groupes_acces
Revises: 0067_pilotage_perimetre
Create Date: 2026-07-05
"""
from __future__ import annotations

from alembic import op

revision = "0068_groupes_acces"
down_revision = "0067_pilotage_perimetre"
branch_labels = None
depends_on = None

_TABLES = ["groupe_acces", "membre_groupe"]
_SELECT = ["super_admin", "admin", "gestionnaire", "controleur", "direction"]
_WRITE = ["super_admin", "admin"]

# Built-in groups, one per platform role. Idempotent seed.
_GROUPES = [
    ("super_administration", "Super administration", "Accès complet à toutes les plateformes", "super_admin"),
    ("administration", "Administration", "Accès administrateur du back-office", "admin"),
    ("gestion_membres", "Gestion des membres", "Gestion des membres, dossiers et inscriptions", "gestionnaire"),
    ("direction", "Direction", "Vue consolidée et pilotage global (lecture)", "direction"),
    ("controle", "Contrôle", "Scan des présences et contrôle sur le terrain", "controleur"),
]


def _array(roles: list[str]) -> str:
    return "ARRAY[" + ", ".join(f"'{r}'" for r in roles) + "]::text[]"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE groupe_acces (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            cle text NOT NULL UNIQUE,
            libelle text NOT NULL,
            description text,
            role_accorde text NOT NULL,
            systeme boolean NOT NULL DEFAULT false,
            actif boolean NOT NULL DEFAULT true,
            cree_le timestamptz DEFAULT now(),
            CONSTRAINT groupe_role_chk CHECK (role_accorde IN ('super_admin', 'admin', 'gestionnaire', 'controleur', 'direction', 'membre'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE membre_groupe (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            membre_id uuid NOT NULL REFERENCES membre(id) ON DELETE CASCADE,
            groupe_id uuid NOT NULL REFERENCES groupe_acces(id) ON DELETE CASCADE,
            ajoute_par uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            ajoute_le timestamptz DEFAULT now(),
            CONSTRAINT membre_groupe_uniq UNIQUE (membre_id, groupe_id)
        )
        """
    )
    op.execute("CREATE INDEX idx_membre_groupe_membre ON membre_groupe(membre_id)")

    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY {table}_select ON {table} FOR SELECT USING (adsum_current_role() = ANY({_array(_SELECT)}))")
        op.execute(f"CREATE POLICY {table}_write ON {table} FOR ALL USING (adsum_current_role() = ANY({_array(_WRITE)})) WITH CHECK (adsum_current_role() = ANY({_array(_WRITE)}))")

    for cle, libelle, desc, role in _GROUPES:
        op.execute(
            "INSERT INTO groupe_acces (cle, libelle, description, role_accorde, systeme) "
            "SELECT %s, %s, %s, %s, true WHERE NOT EXISTS (SELECT 1 FROM groupe_acces WHERE cle = %s)",
            (cle, libelle, desc, role, cle),
        )


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.execute(f"DROP POLICY IF EXISTS {table}_write ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_select ON {table}")
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
