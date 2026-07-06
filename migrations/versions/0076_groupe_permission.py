# ruff: noqa: E501 - migrations carry long SQL and seeded data lines
"""Specialized access groups: a group may grant a named set of permissions.

Extends the access-group model additively. ``groupe_acces.mode`` distinguishes a
historical group that grants a role ('role', the 5 seeded system groups, unchanged)
from a specialized group that grants a permission set ('permissions'). The
specialized groups are seeded here as intermediate, least-privilege tiers between
plain member and full admin. Enforcement (require_permission) is wired separately;
this migration only creates the table, the column and the seed.

Revision ID: 0076_groupe_permission
Revises: 0075_rbac_permissions
Create Date: 2026-07-06
"""
from __future__ import annotations

from alembic import op

revision = "0076_groupe_permission"
down_revision = "0075_rbac_permissions"
branch_labels = None
depends_on = None

_SELECT = ["super_admin", "admin", "gestionnaire", "controleur", "direction"]
_WRITE = ["super_admin", "admin"]

# (cle, libelle, description, [permissions]) - intermediate least-privilege tiers.
SPECIALIZED = [
    ('operateur_inscriptions', 'Operateur inscriptions', "Valider les inscriptions sans modifier l'identite des membres ni gerer les acces.", [
        'inscriptions.gerer',
        'inscriptions.administrer',
        'membres.consulter',
    ]),
    ('editeur_membres', 'Editeur membres', 'Consulter et editer les dossiers membres et traiter leurs demandes.', [
        'membres.consulter',
        'membres.gerer',
        'membres.administrer',
        'demandes.gerer',
        'demandes.superviser',
    ]),
    ('gestionnaire_evenements', 'Gestionnaire evenements', 'Creer et gerer les activites, le comptage et les anniversaires.', [
        'evenements.consulter',
        'evenements.gerer',
        'evenements.superviser',
        'comptage.superviser',
        'comptage.controler',
        'anniversaires.gerer',
    ]),
    ('lecteur_statistiques', 'Lecteur statistiques', "Consulter les statistiques et l'assiduite en lecture seule.", [
        'statistiques.consulter',
        'participation.consulter',
        'evenements.consulter',
    ]),
    ('auditeur', 'Auditeur', "Consulter le journal d'audit en lecture seule.", [
        'audit.administrer',
    ]),
    ('operateur_comptage', 'Operateur comptage', 'Saisir le comptage volet B et scanner les presences.', [
        'comptage.superviser',
        'comptage.controler',
        'controle.controler',
    ]),
    ('administrateur_delegue', 'Administrateur delegue', 'Administre tout sauf la gestion des acces, des comptes et du systeme.', [
        'anniversaires.gerer',
        'attestations.gerer',
        'audit.administrer',
        'bergers.consulter',
        'collaboration.gerer',
        'collaboration.superviser',
        'commissions.administrer',
        'commissions.consulter',
        'comptage.controler',
        'comptage.superviser',
        'consentements.administrer',
        'consentements.consulter',
        'controle.controler',
        'deblocage.superviser',
        'demandes.gerer',
        'demandes.superviser',
        'documents.gerer',
        'doublons.administrer',
        'doublons.consulter',
        'doublons.gerer',
        'evenements.consulter',
        'evenements.gerer',
        'evenements.superviser',
        'fonctions.consulter',
        'fonctions.gerer',
        'inscriptions.administrer',
        'inscriptions.gerer',
        'integrations.administrer',
        'integrations.superviser',
        'matrice-pays.consulter',
        'matrice-pays.gerer',
        'membres.administrer',
        'membres.consulter',
        'membres.gerer',
        'membres.self',
        'modeles.consulter',
        'modeles.gerer',
        'niveaux-engagement.consulter',
        'niveaux-engagement.gerer',
        'notifications.consulter',
        'notifications.gerer',
        'organisation.administrer',
        'organisation.consulter',
        'parametres.consulter',
        'parametres.gerer',
        'participation.consulter',
        'participation.gerer',
        'statistiques.consulter',
        'tags.administrer',
        'terminaux.administrer',
        'terminaux.consulter',
        'tribus.administrer',
        'tribus.consulter',
    ]),
]


def _array(roles):
    return "ARRAY[" + ", ".join(f"'{r}'" for r in roles) + "]::text[]"


def upgrade() -> None:
    op.execute("ALTER TABLE groupe_acces ADD COLUMN IF NOT EXISTS mode text NOT NULL DEFAULT 'role'")
    op.execute("ALTER TABLE groupe_acces DROP CONSTRAINT IF EXISTS groupe_acces_mode_chk")
    op.execute("ALTER TABLE groupe_acces ADD CONSTRAINT groupe_acces_mode_chk CHECK (mode IN ('role', 'permissions'))")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS groupe_permission (
            groupe_id uuid NOT NULL REFERENCES groupe_acces(id) ON DELETE CASCADE,
            permission text NOT NULL REFERENCES permission(cle) ON DELETE CASCADE,
            PRIMARY KEY (groupe_id, permission)
        )
        """
    )
    op.execute("ALTER TABLE groupe_permission ENABLE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY groupe_permission_select ON groupe_permission FOR SELECT USING (adsum_current_role() = ANY({_array(_SELECT)}))")
    op.execute(f"CREATE POLICY groupe_permission_write ON groupe_permission FOR ALL USING (adsum_current_role() = ANY({_array(_WRITE)})) WITH CHECK (adsum_current_role() = ANY({_array(_WRITE)}))")
    for cle, libelle, description, perms in SPECIALIZED:
        op.execute(
            "INSERT INTO groupe_acces (cle, libelle, description, role_accorde, systeme, mode) "
            "VALUES (%s, %s, %s, 'membre', true, 'permissions') "
            "ON CONFLICT (cle) DO UPDATE SET libelle = EXCLUDED.libelle, description = EXCLUDED.description, mode = 'permissions'",
            (cle, libelle, description),
        )
        # Resolve the group id with a subquery so the seed also works offline (--sql).
        for perm in perms:
            op.execute(
                "INSERT INTO groupe_permission (groupe_id, permission) "
                "SELECT ga.id, %s FROM groupe_acces ga WHERE ga.cle = %s ON CONFLICT DO NOTHING",
                (perm, cle),
            )


def downgrade() -> None:
    for cle, *_ in SPECIALIZED:
        op.execute("DELETE FROM groupe_acces WHERE cle = %s AND mode = 'permissions'", (cle,))
    op.execute("DROP POLICY IF EXISTS groupe_permission_write ON groupe_permission")
    op.execute("DROP POLICY IF EXISTS groupe_permission_select ON groupe_permission")
    op.execute("DROP TABLE IF EXISTS groupe_permission CASCADE")
    op.execute("ALTER TABLE groupe_acces DROP CONSTRAINT IF EXISTS groupe_acces_mode_chk")
    op.execute("ALTER TABLE groupe_acces DROP COLUMN IF EXISTS mode")
