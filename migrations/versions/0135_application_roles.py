# ruff: noqa: E501 - migrations carry long SQL lines
"""Per-application roles (LEVEL 2) and their assignment to members.

Access (LEVEL 1, membre_application_acces) is only visibility: a member sees and opens
the application. What they may DO inside is LEVEL 2, the application roles introduced
here. Roles are per application (each app has its own set) and a member can hold several
per app. This table governs the ASSIGNMENT and visibility of roles; the mapping of each
role to concrete permissions/enforcement is layered on progressively (Collaboration, for
instance, already enforces its own space roles). RLS is role-based like the rest.

Revision ID: 0135_application_roles
Revises: 0134_applications_acces
Create Date: 2026-07-13
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0135_application_roles"
down_revision = "0134_applications_acces"
branch_labels = None
depends_on = None

_STAFF = ["super_admin", "admin", "gestionnaire", "controleur", "direction"]
_ALL = [*_STAFF, "membre"]
_ADMIN = ["super_admin", "admin"]

# (application_code, role_code, nom, description). A representative, editable starting set
# per application, aligned with the governance role catalogue.
_ROLES: list[tuple[str, str, str, str]] = [
    ("back-office", "gestionnaire-membres", "Gestionnaire de membres", "Gerer les membres de son perimetre."),
    ("back-office", "gestionnaire-activites", "Gestionnaire d'activites", "Creer, planifier et cloturer les activites autorisees."),
    ("back-office", "gestionnaire-evenements", "Gestionnaire d'evenements", "Gerer les evenements et leur catalogue."),
    ("back-office", "verificateur", "Verificateur de dossiers", "Verifier les dossiers et pieces (avis conforme/non conforme)."),
    ("back-office", "valideur-final", "Valideur final", "Decision finale de validation ou de refus."),
    ("back-office", "lecteur-statistiques", "Lecteur des statistiques", "Consulter les tableaux de bord de son perimetre."),
    ("back-office", "auditeur", "Auditeur", "Acceder aux journaux d'audit (lecture seule)."),
    ("back-office", "administrateur", "Administrateur Back-office", "Operations administratives autorisees."),
    ("collaboration", "proprietaire-espace", "Proprietaire d'espace", "Detenir et administrer ses propres espaces."),
    ("collaboration", "administrateur-espace", "Administrateur d'espace", "Administrer un espace (membres, tableaux, canaux)."),
    ("collaboration", "createur-espace", "Createur d'espace", "Autorise a creer de nouveaux espaces."),
    ("collaboration", "contributeur", "Contributeur", "Contribuer aux tableaux, cartes et canaux d'un espace."),
    ("collaboration", "observateur", "Observateur", "Consulter un espace sans modifier."),
    ("collaboration", "gestionnaire-canal", "Gestionnaire de Canal", "Gerer un canal d'instructions."),
    ("pilotage", "lecteur-tableaux", "Lecteur de tableaux de bord", "Consulter les indicateurs de son perimetre."),
    ("pilotage", "analyste", "Analyste", "Analyser les donnees de son perimetre."),
    ("pilotage", "responsable-commission", "Responsable de commission", "Piloter sa commission dans son perimetre."),
    ("pilotage", "responsable-coordination", "Responsable de coordination", "Piloter sa coordination."),
    ("pilotage", "responsable-intendance", "Responsable d'intendance", "Piloter son intendance."),
    ("pilotage", "administrateur", "Administrateur Pilotage", "Administration de Pilotage."),
    ("direction", "lecteur-kpi", "Lecteur KPI", "Consulter les indicateurs agreges."),
    ("direction", "analyste-direction", "Analyste de direction", "Analyser les syntheses de direction."),
    ("direction", "responsable-direction", "Responsable de direction", "Responsabilite de direction."),
    ("controleur", "controleur-scanner", "Controleur scanner", "Pointer par scan sur les sessions habilitees."),
    ("controleur", "superviseur-controle", "Superviseur de controle", "Gerer les sessions et anomalies de son perimetre."),
    ("controleur", "gestionnaire-terminaux", "Gestionnaire de terminaux", "Gerer les terminaux de scan."),
]


def _array(roles: list[str]) -> str:
    return "ARRAY[" + ", ".join(f"'{r}'" for r in roles) + "]::text[]"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS application_role (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            application_code text NOT NULL REFERENCES application(code) ON DELETE CASCADE,
            code text NOT NULL,
            nom text NOT NULL,
            description text,
            ordre integer NOT NULL DEFAULT 0,
            cree_le timestamptz NOT NULL DEFAULT now(),
            UNIQUE (application_code, code)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS membre_application_role (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            membre_id uuid NOT NULL REFERENCES membre(id) ON DELETE CASCADE,
            application_code text NOT NULL,
            role_code text NOT NULL,
            accorde_le timestamptz NOT NULL DEFAULT now(),
            accorde_par uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            UNIQUE (membre_id, application_code, role_code),
            FOREIGN KEY (application_code, role_code) REFERENCES application_role(application_code, code) ON DELETE CASCADE
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_mar_membre ON membre_application_role(membre_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mar_app ON membre_application_role(application_code)")

    for table, select_roles, write_roles in (
        ("application_role", _ALL, _ADMIN),
        ("membre_application_role", _ALL, _ADMIN),
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON {table} FROM anon")
        op.execute(f"CREATE POLICY {table}_select ON {table} FOR SELECT USING (adsum_current_role() = ANY({_array(select_roles)}))")
        op.execute(f"CREATE POLICY {table}_write ON {table} FOR ALL USING (adsum_current_role() = ANY({_array(write_roles)})) WITH CHECK (adsum_current_role() = ANY({_array(write_roles)}))")

    bind = op.get_bind()
    ins = sa.text("INSERT INTO application_role (application_code, code, nom, description, ordre) VALUES (:app, :code, :nom, :descr, :ordre) ON CONFLICT (application_code, code) DO NOTHING")
    for ordre, (app, code, nom, descr) in enumerate(_ROLES):
        bind.execute(ins, {"app": app, "code": code, "nom": nom, "descr": descr, "ordre": ordre})


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS membre_application_role")
    op.execute("DROP TABLE IF EXISTS application_role")
