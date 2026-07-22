# ruff: noqa: E501 - migrations carry long SQL lines
"""Correct accents and document the coverage of every standard (system) access group.

The system groups are read-only references shown in the back office "Access & groups"
page. Several descriptions were missing French diacritics (a client-facing defect) and
none stated which applications or areas the group actually grants. This migration
rewrites each description with correct accents and an explicit "Applications:" clause,
so an administrator can see at a glance what a standard group covers before granting it.
No permission is changed: only the human-readable description of each system group.

Revision ID: 0170_groupes_standard_doc
Revises: 0169_fonctions_manquantes
Create Date: 2026-07-22
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0170_groupes_standard_doc"
down_revision = "0169_fonctions_manquantes"
branch_labels = None
depends_on = None

# Each standard group: corrected, accent-correct description that documents what it
# grants and the applications or areas it covers.
_DESCRIPTIONS = {
    "super_administration": "Accès complet à toutes les plateformes (back-office, direction, pilotage, collaboration, contrôle). Tous les pouvoirs système, y compris comptes et sécurité. À réserver au strict nécessaire.",
    "administration": "Administration du back-office : membres, activités, organisation et communication. Ne couvre pas la super-administration (comptes système, sécurité, accès). Application : back-office.",
    "administrateur_delegue": "Administre l'ensemble du back-office sauf la gestion des accès, des comptes et du système. Application : back-office.",
    "direction": "Vue consolidée et pilotage en lecture seule, sans modification des données. Applications : direction, tableau de bord et statistiques.",
    "controle": "Scan des présences et contrôle sur le terrain, y compris hors ligne. Application : contrôle (mobile).",
    "gestion_membres": "Gestion des membres, des dossiers et des inscriptions. Application : back-office (annuaire et inscriptions).",
    "editeur_membres": "Consulter et éditer les dossiers membres et traiter leurs demandes. Application : back-office (annuaire).",
    "operateur_inscriptions": "Valider les inscriptions sans modifier l'identité des membres ni gérer les accès. Application : back-office (inscriptions).",
    "gestionnaire_evenements": "Créer et gérer les activités, le comptage et les anniversaires. Application : back-office (événements et comptage).",
    "operateur_comptage": "Saisir le comptage volet B et scanner les présences. Applications : back-office (comptage) et contrôle.",
    "lecteur_statistiques": "Consulter les statistiques et l'assiduité en lecture seule. Applications : back-office et direction (lecture).",
    "auditeur": "Consulter le journal d'audit en lecture seule, sans autre pouvoir. Application : back-office (journal d'audit).",
}

# Accent-correct labels for the system groups whose libelle was missing diacritics.
_LIBELLES = {
    "administrateur_delegue": "Administrateur délégué",
    "editeur_membres": "Éditeur membres",
    "gestionnaire_evenements": "Gestionnaire événements",
    "operateur_comptage": "Opérateur comptage",
    "operateur_inscriptions": "Opérateur inscriptions",
    "super_administration": "Super administration",
}


def upgrade() -> None:
    bind = op.get_bind()
    stmt_d = sa.text("UPDATE groupe_acces SET description = :v WHERE cle = :c AND systeme = true")
    for cle, description in _DESCRIPTIONS.items():
        bind.execute(stmt_d, {"v": description, "c": cle})
    stmt_l = sa.text("UPDATE groupe_acces SET libelle = :v WHERE cle = :c AND systeme = true")
    for cle, libelle in _LIBELLES.items():
        bind.execute(stmt_l, {"v": libelle, "c": cle})


def downgrade() -> None:
    # Descriptions are documentation only; the previous text is not restored.
    pass
