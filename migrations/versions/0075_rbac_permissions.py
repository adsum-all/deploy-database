# ruff: noqa: E501 - migrations carry long SQL and seeded data lines
"""Fine-grained permission catalogue and the historical-role compatibility mapping.

Adds the executory permission model UNDER the existing role enforcement, without
removing anything. ``permission`` is the catalogue (domaine.action, risk, scope),
seeded from the real endpoint matrix. ``role_permission`` maps each historical
role to exactly the permissions covering the endpoints that role reaches today, so
switching an endpoint from ``require_roles`` to ``require_permission`` admits the
SAME accounts (iso-behaviour, proven by the conformity test). This migration only
creates and seeds the tables; enforcement is wired in a later change.

Revision ID: 0075_rbac_permissions
Revises: 0074_evenement_fuseau
Create Date: 2026-07-06
"""
from __future__ import annotations

from alembic import op

revision = "0075_rbac_permissions"
down_revision = "0074_evenement_fuseau"
branch_labels = None
depends_on = None

_SELECT = ["super_admin", "admin", "gestionnaire", "controleur", "direction"]
_WRITE = ["super_admin", "admin"]

# (cle, domaine, libelle, risque, portee) - generated from the real endpoint matrix.
PERMISSIONS = [
    ('acces.administrer', 'acces', 'Acces et groupes - administrer', 'critique', 'global'),
    ('acces.systeme', 'acces', 'Acces et groupes - administration systeme', 'critique', 'global'),
    ('anniversaires.gerer', 'anniversaires', 'Anniversaires - gerer', 'moyen', 'scope'),
    ('attestations.gerer', 'attestations', 'Attestations - gerer', 'moyen', 'scope'),
    ('audit.administrer', 'audit', "Journal d'audit - administrer", 'eleve', 'global'),
    ('bergers.consulter', 'bergers', 'Bergers - consulter', 'faible', 'scope'),
    ('collaboration.gerer', 'collaboration', 'Collaboration - gerer', 'moyen', 'scope'),
    ('collaboration.superviser', 'collaboration', 'Collaboration - superviser', 'faible', 'scope'),
    ('commissions.administrer', 'commissions', 'Commissions et missions - administrer', 'eleve', 'scope'),
    ('commissions.consulter', 'commissions', 'Commissions et missions - consulter', 'faible', 'scope'),
    ('comptage.controler', 'comptage', 'Comptage - controler', 'moyen', 'scope'),
    ('comptage.superviser', 'comptage', 'Comptage - superviser', 'faible', 'scope'),
    ('comptes.administrer', 'comptes', 'Comptes - administrer', 'critique', 'global'),
    ('comptes.systeme', 'comptes', 'Comptes - administration systeme', 'critique', 'global'),
    ('consentements.administrer', 'consentements', 'Consentements - administrer', 'eleve', 'global'),
    ('consentements.consulter', 'consentements', 'Consentements - consulter', 'faible', 'scope'),
    ('controle.controler', 'controle', 'Controle - controler', 'moyen', 'scope'),
    ('deblocage.superviser', 'deblocage', 'Deblocage - superviser', 'faible', 'scope'),
    ('demandes.gerer', 'demandes', 'Demandes - gerer', 'moyen', 'scope'),
    ('demandes.superviser', 'demandes', 'Demandes - superviser', 'faible', 'scope'),
    ('documents.gerer', 'documents', 'Documents - gerer', 'moyen', 'scope'),
    ('doublons.administrer', 'doublons', 'Doublons - administrer', 'critique', 'global'),
    ('doublons.consulter', 'doublons', 'Doublons - consulter', 'critique', 'global'),
    ('doublons.gerer', 'doublons', 'Doublons - gerer', 'critique', 'global'),
    ('evenements.consulter', 'evenements', 'Evenements - consulter', 'faible', 'scope'),
    ('evenements.gerer', 'evenements', 'Evenements - gerer', 'moyen', 'scope'),
    ('evenements.superviser', 'evenements', 'Evenements - superviser', 'faible', 'scope'),
    ('fonctions.consulter', 'fonctions', 'Fonctions et titres - consulter', 'faible', 'scope'),
    ('fonctions.gerer', 'fonctions', 'Fonctions et titres - gerer', 'moyen', 'scope'),
    ('inscriptions.administrer', 'inscriptions', 'Inscriptions - administrer', 'eleve', 'scope'),
    ('inscriptions.gerer', 'inscriptions', 'Inscriptions - gerer', 'moyen', 'scope'),
    ('integrations.administrer', 'integrations', 'Integrations - administrer', 'eleve', 'global'),
    ('integrations.superviser', 'integrations', 'Integrations - superviser', 'faible', 'scope'),
    ('matrice-pays.consulter', 'matrice-pays', 'Matrice pays - consulter', 'faible', 'scope'),
    ('matrice-pays.gerer', 'matrice-pays', 'Matrice pays - gerer', 'moyen', 'scope'),
    ('membres.administrer', 'membres', 'Membres - administrer', 'eleve', 'scope'),
    ('membres.consulter', 'membres', 'Membres - consulter', 'moyen', 'scope'),
    ('membres.gerer', 'membres', 'Membres - gerer', 'moyen', 'scope'),
    ('membres.self', 'membres', 'Membres - acces personnel', 'faible', 'self'),
    ('modeles.consulter', 'modeles', 'Modeles - consulter', 'faible', 'scope'),
    ('modeles.gerer', 'modeles', 'Modeles - gerer', 'moyen', 'scope'),
    ('niveaux-engagement.consulter', 'niveaux-engagement', 'Niveaux-Engagement - consulter', 'faible', 'scope'),
    ('niveaux-engagement.gerer', 'niveaux-engagement', 'Niveaux-Engagement - gerer', 'moyen', 'scope'),
    ('notifications.consulter', 'notifications', 'Notifications - consulter', 'faible', 'scope'),
    ('notifications.gerer', 'notifications', 'Notifications - gerer', 'moyen', 'scope'),
    ('organisation.administrer', 'organisation', 'Organisation - administrer', 'eleve', 'global'),
    ('organisation.consulter', 'organisation', 'Organisation - consulter', 'faible', 'scope'),
    ('parametres.consulter', 'parametres', 'Parametres - consulter', 'faible', 'scope'),
    ('parametres.gerer', 'parametres', 'Parametres - gerer', 'moyen', 'scope'),
    ('participation.consulter', 'participation', 'Participation - consulter', 'moyen', 'scope'),
    ('participation.gerer', 'participation', 'Participation - gerer', 'moyen', 'scope'),
    ('statistiques.consulter', 'statistiques', 'Statistiques - consulter', 'moyen', 'scope'),
    ('tags.administrer', 'tags', 'Etiquettes - administrer', 'eleve', 'global'),
    ('terminaux.administrer', 'terminaux', 'Terminaux - administrer', 'eleve', 'global'),
    ('terminaux.consulter', 'terminaux', 'Terminaux - consulter', 'faible', 'scope'),
    ('tribus.administrer', 'tribus', 'Tribus - administrer', 'eleve', 'scope'),
    ('tribus.consulter', 'tribus', 'Tribus - consulter', 'faible', 'scope'),
]

# (role, permission_cle) - role R holds P iff R is admitted by every endpoint P covers.
ROLE_PERMISSION = [
    ('admin', 'acces.administrer'),
    ('admin', 'anniversaires.gerer'),
    ('admin', 'attestations.gerer'),
    ('admin', 'audit.administrer'),
    ('admin', 'bergers.consulter'),
    ('admin', 'collaboration.gerer'),
    ('admin', 'collaboration.superviser'),
    ('admin', 'commissions.administrer'),
    ('admin', 'commissions.consulter'),
    ('admin', 'comptage.controler'),
    ('admin', 'comptage.superviser'),
    ('admin', 'comptes.administrer'),
    ('admin', 'consentements.administrer'),
    ('admin', 'consentements.consulter'),
    ('admin', 'controle.controler'),
    ('admin', 'deblocage.superviser'),
    ('admin', 'demandes.gerer'),
    ('admin', 'demandes.superviser'),
    ('admin', 'documents.gerer'),
    ('admin', 'doublons.administrer'),
    ('admin', 'doublons.consulter'),
    ('admin', 'doublons.gerer'),
    ('admin', 'evenements.consulter'),
    ('admin', 'evenements.gerer'),
    ('admin', 'evenements.superviser'),
    ('admin', 'fonctions.consulter'),
    ('admin', 'fonctions.gerer'),
    ('admin', 'inscriptions.administrer'),
    ('admin', 'inscriptions.gerer'),
    ('admin', 'integrations.administrer'),
    ('admin', 'integrations.superviser'),
    ('admin', 'matrice-pays.consulter'),
    ('admin', 'matrice-pays.gerer'),
    ('admin', 'membres.administrer'),
    ('admin', 'membres.consulter'),
    ('admin', 'membres.gerer'),
    ('admin', 'membres.self'),
    ('admin', 'modeles.consulter'),
    ('admin', 'modeles.gerer'),
    ('admin', 'niveaux-engagement.consulter'),
    ('admin', 'niveaux-engagement.gerer'),
    ('admin', 'notifications.consulter'),
    ('admin', 'notifications.gerer'),
    ('admin', 'organisation.administrer'),
    ('admin', 'organisation.consulter'),
    ('admin', 'parametres.consulter'),
    ('admin', 'parametres.gerer'),
    ('admin', 'participation.consulter'),
    ('admin', 'participation.gerer'),
    ('admin', 'statistiques.consulter'),
    ('admin', 'tags.administrer'),
    ('admin', 'terminaux.administrer'),
    ('admin', 'terminaux.consulter'),
    ('admin', 'tribus.administrer'),
    ('admin', 'tribus.consulter'),
    ('controleur', 'bergers.consulter'),
    ('controleur', 'commissions.consulter'),
    ('controleur', 'comptage.controler'),
    ('controleur', 'consentements.consulter'),
    ('controleur', 'controle.controler'),
    ('controleur', 'doublons.consulter'),
    ('controleur', 'evenements.consulter'),
    ('controleur', 'fonctions.consulter'),
    ('controleur', 'matrice-pays.consulter'),
    ('controleur', 'membres.consulter'),
    ('controleur', 'membres.self'),
    ('controleur', 'modeles.consulter'),
    ('controleur', 'niveaux-engagement.consulter'),
    ('controleur', 'notifications.consulter'),
    ('controleur', 'organisation.consulter'),
    ('controleur', 'parametres.consulter'),
    ('controleur', 'participation.consulter'),
    ('controleur', 'statistiques.consulter'),
    ('controleur', 'terminaux.consulter'),
    ('controleur', 'tribus.consulter'),
    ('direction', 'bergers.consulter'),
    ('direction', 'collaboration.superviser'),
    ('direction', 'commissions.consulter'),
    ('direction', 'comptage.superviser'),
    ('direction', 'consentements.consulter'),
    ('direction', 'deblocage.superviser'),
    ('direction', 'demandes.superviser'),
    ('direction', 'doublons.consulter'),
    ('direction', 'evenements.consulter'),
    ('direction', 'evenements.superviser'),
    ('direction', 'fonctions.consulter'),
    ('direction', 'integrations.superviser'),
    ('direction', 'matrice-pays.consulter'),
    ('direction', 'membres.consulter'),
    ('direction', 'membres.self'),
    ('direction', 'modeles.consulter'),
    ('direction', 'niveaux-engagement.consulter'),
    ('direction', 'notifications.consulter'),
    ('direction', 'organisation.consulter'),
    ('direction', 'parametres.consulter'),
    ('direction', 'participation.consulter'),
    ('direction', 'statistiques.consulter'),
    ('direction', 'terminaux.consulter'),
    ('direction', 'tribus.consulter'),
    ('gestionnaire', 'anniversaires.gerer'),
    ('gestionnaire', 'attestations.gerer'),
    ('gestionnaire', 'bergers.consulter'),
    ('gestionnaire', 'collaboration.gerer'),
    ('gestionnaire', 'collaboration.superviser'),
    ('gestionnaire', 'commissions.consulter'),
    ('gestionnaire', 'comptage.controler'),
    ('gestionnaire', 'comptage.superviser'),
    ('gestionnaire', 'consentements.consulter'),
    ('gestionnaire', 'controle.controler'),
    ('gestionnaire', 'deblocage.superviser'),
    ('gestionnaire', 'demandes.gerer'),
    ('gestionnaire', 'demandes.superviser'),
    ('gestionnaire', 'documents.gerer'),
    ('gestionnaire', 'doublons.consulter'),
    ('gestionnaire', 'doublons.gerer'),
    ('gestionnaire', 'evenements.consulter'),
    ('gestionnaire', 'evenements.gerer'),
    ('gestionnaire', 'evenements.superviser'),
    ('gestionnaire', 'fonctions.consulter'),
    ('gestionnaire', 'fonctions.gerer'),
    ('gestionnaire', 'inscriptions.gerer'),
    ('gestionnaire', 'integrations.superviser'),
    ('gestionnaire', 'matrice-pays.consulter'),
    ('gestionnaire', 'matrice-pays.gerer'),
    ('gestionnaire', 'membres.consulter'),
    ('gestionnaire', 'membres.gerer'),
    ('gestionnaire', 'membres.self'),
    ('gestionnaire', 'modeles.consulter'),
    ('gestionnaire', 'modeles.gerer'),
    ('gestionnaire', 'niveaux-engagement.consulter'),
    ('gestionnaire', 'niveaux-engagement.gerer'),
    ('gestionnaire', 'notifications.consulter'),
    ('gestionnaire', 'notifications.gerer'),
    ('gestionnaire', 'organisation.consulter'),
    ('gestionnaire', 'parametres.consulter'),
    ('gestionnaire', 'parametres.gerer'),
    ('gestionnaire', 'participation.consulter'),
    ('gestionnaire', 'participation.gerer'),
    ('gestionnaire', 'statistiques.consulter'),
    ('gestionnaire', 'terminaux.consulter'),
    ('gestionnaire', 'tribus.consulter'),
    ('membre', 'membres.self'),
    ('super_admin', 'acces.administrer'),
    ('super_admin', 'acces.systeme'),
    ('super_admin', 'anniversaires.gerer'),
    ('super_admin', 'attestations.gerer'),
    ('super_admin', 'audit.administrer'),
    ('super_admin', 'bergers.consulter'),
    ('super_admin', 'collaboration.gerer'),
    ('super_admin', 'collaboration.superviser'),
    ('super_admin', 'commissions.administrer'),
    ('super_admin', 'commissions.consulter'),
    ('super_admin', 'comptage.controler'),
    ('super_admin', 'comptage.superviser'),
    ('super_admin', 'comptes.administrer'),
    ('super_admin', 'comptes.systeme'),
    ('super_admin', 'consentements.administrer'),
    ('super_admin', 'consentements.consulter'),
    ('super_admin', 'controle.controler'),
    ('super_admin', 'deblocage.superviser'),
    ('super_admin', 'demandes.gerer'),
    ('super_admin', 'demandes.superviser'),
    ('super_admin', 'documents.gerer'),
    ('super_admin', 'doublons.administrer'),
    ('super_admin', 'doublons.consulter'),
    ('super_admin', 'doublons.gerer'),
    ('super_admin', 'evenements.consulter'),
    ('super_admin', 'evenements.gerer'),
    ('super_admin', 'evenements.superviser'),
    ('super_admin', 'fonctions.consulter'),
    ('super_admin', 'fonctions.gerer'),
    ('super_admin', 'inscriptions.administrer'),
    ('super_admin', 'inscriptions.gerer'),
    ('super_admin', 'integrations.administrer'),
    ('super_admin', 'integrations.superviser'),
    ('super_admin', 'matrice-pays.consulter'),
    ('super_admin', 'matrice-pays.gerer'),
    ('super_admin', 'membres.administrer'),
    ('super_admin', 'membres.consulter'),
    ('super_admin', 'membres.gerer'),
    ('super_admin', 'membres.self'),
    ('super_admin', 'modeles.consulter'),
    ('super_admin', 'modeles.gerer'),
    ('super_admin', 'niveaux-engagement.consulter'),
    ('super_admin', 'niveaux-engagement.gerer'),
    ('super_admin', 'notifications.consulter'),
    ('super_admin', 'notifications.gerer'),
    ('super_admin', 'organisation.administrer'),
    ('super_admin', 'organisation.consulter'),
    ('super_admin', 'parametres.consulter'),
    ('super_admin', 'parametres.gerer'),
    ('super_admin', 'participation.consulter'),
    ('super_admin', 'participation.gerer'),
    ('super_admin', 'statistiques.consulter'),
    ('super_admin', 'tags.administrer'),
    ('super_admin', 'terminaux.administrer'),
    ('super_admin', 'terminaux.consulter'),
    ('super_admin', 'tribus.administrer'),
    ('super_admin', 'tribus.consulter'),
]


def _array(roles):
    return "ARRAY[" + ", ".join(f"'{r}'" for r in roles) + "]::text[]"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS permission (
            cle text PRIMARY KEY,
            domaine text NOT NULL,
            libelle text NOT NULL,
            description text,
            risque text NOT NULL CHECK (risque IN ('faible', 'moyen', 'eleve', 'critique')),
            portee text NOT NULL CHECK (portee IN ('self', 'scope', 'global')),
            systeme boolean NOT NULL DEFAULT true
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS role_permission (
            role text NOT NULL CHECK (role IN ('membre', 'controleur', 'gestionnaire', 'direction', 'admin', 'super_admin')),
            permission text NOT NULL REFERENCES permission(cle) ON DELETE CASCADE,
            PRIMARY KEY (role, permission)
        )
        """
    )
    for table in ("permission", "role_permission"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY {table}_select ON {table} FOR SELECT USING (adsum_current_role() = ANY({_array(_SELECT)}))")
        op.execute(f"CREATE POLICY {table}_write ON {table} FOR ALL USING (adsum_current_role() = ANY({_array(_WRITE)})) WITH CHECK (adsum_current_role() = ANY({_array(_WRITE)}))")
    for cle, domaine, libelle, risque, portee in PERMISSIONS:
        op.execute(
            "INSERT INTO permission (cle, domaine, libelle, risque, portee, systeme) VALUES (%s, %s, %s, %s, %s, true) "
            "ON CONFLICT (cle) DO UPDATE SET domaine = EXCLUDED.domaine, libelle = EXCLUDED.libelle, risque = EXCLUDED.risque, portee = EXCLUDED.portee",
            (cle, domaine, libelle, risque, portee),
        )
    for role, permission in ROLE_PERMISSION:
        op.execute(
            "INSERT INTO role_permission (role, permission) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (role, permission),
        )


def downgrade() -> None:
    for table in ("role_permission", "permission"):
        op.execute(f"DROP POLICY IF EXISTS {table}_write ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_select ON {table}")
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
