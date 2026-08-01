# ruff: noqa: E501 - migrations carry long SQL lines
"""Write the functional documentation of every standard access group.

Migration 0170 corrected their wording and stated which applications they cover.
This one fills the columns added by 0172 so an administrator can read, before
granting anything, what a group is for, who it is meant for, when it should not be
used, how far it reaches and what it puts at risk. Documentation only: no permission,
no membership and no schema is changed.

Revision ID: 0173_groupes_standard_finalite
Revises: 0172_groupes_doc_duplication
Create Date: 2026-07-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0173_groupes_standard_finalite"
down_revision = "0172_groupes_doc_duplication"
branch_labels = None
depends_on = None

# cle -> (finalite, usage recommande, usage deconseille, portee, avertissement)
_DOC = {
    "super_administration": (
        "Détenir la totalité des pouvoirs de la plateforme, y compris la gestion des comptes, des accès et des paramètres de sécurité.",
        "À réserver à une ou deux personnes de confiance assurant l'administration système et la continuité de service.",
        "Ne jamais accorder pour un besoin métier courant, ni pour dépanner ponctuellement : préférer un groupe ciblé.",
        "Toute la base, toutes les applications, sans restriction de périmètre.",
        "Pouvoir maximal : un titulaire peut modifier les droits de tous les autres, y compris les siens. Limiter le nombre de titulaires et surveiller le journal d'audit.",
    ),
    "administration": (
        "Administrer le back-office au quotidien : membres, activités, organisation et communication.",
        "Pour un administrateur fonctionnel qui pilote la vie de l'organisation sans toucher au système.",
        "Ne convient pas si la personne ne doit voir qu'un périmètre précis : utiliser plutôt un groupe de permissions à périmètre limité.",
        "Toute la base pour les domaines fonctionnels, hors comptes, accès et sécurité.",
        "Large pouvoir de modification des données des membres. Ne couvre pas la gestion des accès, ce qui est voulu.",
    ),
    "administrateur_delegue": (
        "Administrer l'ensemble du back-office en laissant volontairement de côté la gestion des accès, des comptes et du système.",
        "Pour déléguer l'administration fonctionnelle en conservant la séparation des tâches sur la sécurité.",
        "Ne pas utiliser lorsque la personne doit aussi gérer les groupes et les comptes.",
        "Toute la base pour les domaines fonctionnels.",
        "Séparation des tâches : ce groupe existe précisément pour ne pas cumuler administration fonctionnelle et administration des accès.",
    ),
    "direction": (
        "Donner une vue consolidée et un pilotage en lecture, sans aucun pouvoir de modification.",
        "Pour les membres de la direction et les responsables qui suivent les indicateurs.",
        "Ne pas utiliser pour quelqu'un devant saisir ou corriger des données.",
        "Lecture sur toute la base, applications direction, tableau de bord et statistiques.",
        "Lecture seule, mais la vue est globale : les données consultées restent personnelles et soumises au RGPD.",
    ),
    "controle": (
        "Opérer le contrôle de présence sur le terrain, y compris hors ligne.",
        "Pour les contrôleurs lors des activités, sur mobile.",
        "Ne pas utiliser pour gérer les membres ou consulter les statistiques.",
        "Borné aux événements du périmètre de contrôle attribué.",
        "Accès mobile utilisé sur le terrain : veiller au verrouillage de l'appareil et à la révocation rapide en cas de perte.",
    ),
    "gestion_membres": (
        "Gérer les membres, leurs dossiers et leurs inscriptions.",
        "Pour le secrétariat et les gestionnaires de l'annuaire.",
        "Ne pas utiliser pour accorder des accès applicatifs : cela relève de la gestion des accès.",
        "Annuaire et inscriptions, dans le périmètre attribué.",
        "Donne accès à de nombreuses données personnelles : tracer les consultations et limiter le périmètre.",
    ),
    "editeur_membres": (
        "Consulter et éditer les dossiers des membres et traiter leurs demandes.",
        "Pour un agent qui met à jour les dossiers sans créer ni supprimer de membre.",
        "Ne pas utiliser si la personne doit créer, supprimer ou bloquer des membres.",
        "Annuaire, dans le périmètre attribué.",
        "Modification de données personnelles : chaque changement doit rester traçable.",
    ),
    "operateur_inscriptions": (
        "Valider les inscriptions sans modifier l'identité des membres ni gérer les accès.",
        "Pour les opérateurs de campagne d'inscription.",
        "Ne pas utiliser pour corriger une identité : cela relève de l'édition des membres.",
        "Inscriptions, dans le périmètre attribué.",
        "Décision d'admission : vérifier la pièce justificative avant de valider.",
    ),
    "gestionnaire_evenements": (
        "Créer et gérer les activités, le comptage et les anniversaires.",
        "Pour les organisateurs d'activités et de rencontres.",
        "Ne pas utiliser pour gérer les membres eux-mêmes.",
        "Événements et comptage, dans le périmètre attribué.",
        "La diffusion d'une activité peut déclencher des notifications de masse : vérifier le ciblage avant publication.",
    ),
    "operateur_comptage": (
        "Saisir le comptage et scanner les présences.",
        "Pour les équipes de comptage pendant une activité.",
        "Ne pas utiliser pour consulter le comptage consolidé ni gérer les événements.",
        "Comptage, dans le périmètre attribué, et application de contrôle.",
        "Saisie de terrain : une erreur de comptage fausse les statistiques de participation.",
    ),
    "lecteur_statistiques": (
        "Consulter les statistiques et l'assiduité, en lecture seule.",
        "Pour un observateur ou un analyste qui n'a pas besoin des dossiers nominatifs.",
        "Ne pas utiliser lorsque la personne doit agir sur les données.",
        "Lecture des indicateurs, back-office et direction.",
        "Même agrégées, les statistiques peuvent révéler des situations individuelles dans un petit effectif.",
    ),
    "auditeur": (
        "Consulter le journal d'audit, sans aucun autre pouvoir.",
        "Pour un contrôle interne ou une revue de conformité.",
        "Ne pas utiliser pour un besoin opérationnel : ce groupe ne donne accès à aucune donnée métier.",
        "Journal d'audit uniquement.",
        "Le journal contient qui a fait quoi : sa consultation doit elle-même rester exceptionnelle et justifiée.",
    ),
}


def upgrade() -> None:
    bind = op.get_bind()
    stmt = sa.text(
        "UPDATE groupe_acces SET finalite = :f, usage_recommande = :ur, usage_deconseille = :ud, "
        "portee_texte = :p, avertissement_securite = :a WHERE cle = :c AND systeme = true"
    )
    for cle, (finalite, ur, ud, portee, avert) in _DOC.items():
        bind.execute(stmt, {"f": finalite, "ur": ur, "ud": ud, "p": portee, "a": avert, "c": cle})


def downgrade() -> None:
    op.execute(
        "UPDATE groupe_acces SET finalite = NULL, usage_recommande = NULL, usage_deconseille = NULL, "
        "portee_texte = NULL, avertissement_securite = NULL WHERE systeme = true"
    )
