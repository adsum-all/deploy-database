# ruff: noqa: E501 - migrations carry long SQL lines
"""Per-member application access: the source of truth for « Mes applications ».

Introduces the application catalogue and an explicit, auditable member-to-application
access grant. Seeing an application (this grant) is distinct from what the member can
do inside it (RBAC roles) and from which data they see (perimeter scoping): this table
only governs LEVEL 1 (visibility/access to the application). No access is implicit; a
member sees an application only when an active grant exists. RLS is role-based like the
rest of the schema; the member self-endpoint additionally restricts to their own rows.

Revision ID: 0134_applications_acces
Revises: 0133_niveau_technique
Create Date: 2026-07-13
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0134_applications_acces"
down_revision = "0133_niveau_technique"
branch_labels = None
depends_on = None

_STAFF = ["super_admin", "admin", "gestionnaire", "controleur", "direction"]
_ALL = [*_STAFF, "membre"]
_ADMIN = ["super_admin", "admin"]

# (code, nom, description, url). Additional applications a member can be granted access
# to, beyond the member app which is their own home. URLs are the live deployments.
_APPS: list[tuple[str, str, str, str]] = [
    ("back-office", "ADSUM Back-office", "Administration : membres, organisation, evenements, gouvernance.", "https://adsum-back-office.pages.dev"),
    ("collaboration", "ADSUM Collaboration", "Espaces, tableaux, cartes, canaux et activites partagees.", "https://adsum-collaboration.pages.dev"),
    ("pilotage", "ADSUM Pilotage", "Tableaux de bord et suivi par perimetre (coordination, intendance, commission).", "https://adsum-pilotage.pages.dev"),
    ("direction", "ADSUM Direction", "Syntheses, indicateurs et vues de direction.", "https://adsum-direction.pages.dev"),
    ("controleur", "ADSUM Controleur", "Pointage par scan, sessions et anomalies de controle.", "https://adsum-controleur.pages.dev"),
]


def _array(roles: list[str]) -> str:
    return "ARRAY[" + ", ".join(f"'{r}'" for r in roles) + "]::text[]"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS application (
            code text PRIMARY KEY,
            nom text NOT NULL,
            description text,
            url text,
            actif boolean NOT NULL DEFAULT true,
            ordre integer NOT NULL DEFAULT 0,
            cree_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS membre_application_acces (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            membre_id uuid NOT NULL REFERENCES membre(id) ON DELETE CASCADE,
            application_code text NOT NULL REFERENCES application(code) ON DELETE CASCADE,
            actif boolean NOT NULL DEFAULT true,
            accorde_le timestamptz NOT NULL DEFAULT now(),
            accorde_par uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            revoque_le timestamptz,
            revoque_par uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            motif text,
            maj_le timestamptz NOT NULL DEFAULT now(),
            UNIQUE (membre_id, application_code)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_maa_membre ON membre_application_acces(membre_id)")

    # RLS, consistent with the rest of the schema (role-based via adsum_current_role()).
    for table, select_roles, write_roles in (
        ("application", _ALL, _ADMIN),
        ("membre_application_acces", _ALL, _ADMIN),
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON {table} FROM anon")
        op.execute(f"CREATE POLICY {table}_select ON {table} FOR SELECT USING (adsum_current_role() = ANY({_array(select_roles)}))")
        op.execute(f"CREATE POLICY {table}_write ON {table} FOR ALL USING (adsum_current_role() = ANY({_array(write_roles)})) WITH CHECK (adsum_current_role() = ANY({_array(write_roles)}))")

    bind = op.get_bind()
    ins = sa.text("INSERT INTO application (code, nom, description, url, actif, ordre) VALUES (:code, :nom, :description, :url, true, :ordre) ON CONFLICT (code) DO NOTHING")
    for ordre, (code, nom, description, url) in enumerate(_APPS):
        bind.execute(ins, {"code": code, "nom": nom, "description": description, "url": url, "ordre": ordre})


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS membre_application_acces")
    op.execute("DROP TABLE IF EXISTS application")
