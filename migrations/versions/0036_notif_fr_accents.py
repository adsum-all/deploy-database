# ruff: noqa: E501 - migrations carry long SQL and seeded text lines
"""Fix French accents on the membership-workflow notification templates.

Migrations 0027, 0028 and 0030 seeded a subset of templates without their
diacritics (reçu, adhésion, signée, électronique, échéance, célébrons, vœux...).
Those rows were inserted with ``ON CONFLICT DO NOTHING``, so correcting the
source migrations does not rewrite the live rows. This migration rewrites them
with irreproachable French of France. Idempotent: it simply sets the final text.

Revision ID: 0036_notif_fr_accents
Revises: 0035_code_usage
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0036_notif_fr_accents"
down_revision = "0035_code_usage"
branch_labels = None
depends_on = None

# (cle, titre, corps) with correct diacritics.
_TEMPLATES = [
    ("inscription_soumise",
     "Dossier d'adhésion bien reçu",
     "Bonjour {prenom}, nous confirmons la bonne réception de votre dossier d'adhésion. Il a été transmis à l'administration et sera étudié avec attention. Vous serez informé(e) de la suite par ce même canal. Merci de votre engagement."),
    ("engagement_code",
     "Votre code de signature électronique",
     "Bonjour {prenom}, voici votre code de signature électronique : {code}. Saisissez-le dans l'application pour valider votre lecture et votre acceptation des documents. Il est valable quelques minutes et strictement personnel."),
    ("attestation_requise",
     "Attestation signée à retourner",
     "Bonjour {prenom}, votre adhésion est validée. Conformément à la réglementation applicable dans votre pays, une attestation d'engagement signée de votre main est requise. Téléchargez-la dans votre espace, signez-la, puis renvoyez-la via l'application avant le {echeance}."),
    ("attestation_rappel",
     "Rappel : attestation signée à retourner",
     "Bonjour {prenom}, il vous reste peu de temps pour retourner votre attestation d'engagement signée (échéance : {echeance}). Merci de la déposer dans l'application pour finaliser votre dossier."),
    ("attestation_expiree",
     "Attestation non retournée : dossier suspendu",
     "Bonjour {prenom}, l'attestation d'engagement signée n'a pas été reçue dans le délai imparti. Votre dossier est suspendu. Contactez l'administration pour régulariser votre situation."),
    ("correction_demandee",
     "Votre dossier nécessite une correction",
     "Bonjour {prenom}, l'administration vous demande de corriger votre dossier d'adhésion. Motif : {motif}. Vos informations sont conservées : rouvrez votre dossier dans l'application, corrigez uniquement ce qui est demandé, puis renvoyez-le. Merci."),
    ("anniversaire_pairs",
     "Anniversaires du jour",
     "Aujourd'hui, nous célébrons : {liste}. Prenez un instant pour adresser vos vœux fraternels."),
    ("activite_test_diffusion",
     "Test de diffusion en live : {titre}",
     "Ceci est un test de diffusion en live pour {titre}. La session ouvrira bientôt. (Test de diffusion en live.)"),
]

# (cle, libelle) corrected type_notification labels.
_TYPES = [
    ("inscription_soumise", "Dossier d'adhésion reçu"),
    ("engagement_code", "Code de signature électronique"),
    ("attestation_requise", "Attestation signée requise"),
    ("attestation_rappel", "Rappel attestation signée"),
    ("attestation_expiree", "Attestation non retournée"),
    ("correction_demandee", "Correction du dossier demandée"),
]


def upgrade() -> None:
    for cle, titre, corps in _TEMPLATES:
        op.execute(
            "UPDATE modele_message SET titre = %s, corps = %s WHERE cle = %s",
            (titre, corps, cle),
        )
    for cle, libelle in _TYPES:
        op.execute(
            "UPDATE type_notification SET libelle = %s WHERE cle = %s",
            (libelle, cle),
        )


def downgrade() -> None:
    # No-op: the previous (unaccented) text is not restored.
    pass
