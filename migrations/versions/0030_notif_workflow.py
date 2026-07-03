"""Registration workflow notifications (submission, signature code, attestation,
correction) as bilingual, multi-channel notification types.

Wires the acknowledgement of a submitted dossier and the other onboarding events
into the multi-channel engine (in-app + e-mail + Telegram) instead of the
in-app-only helper that was used before, so a member who submits their file
actually receives an e-mail confirmation.

Revision ID: 0030_notif_workflow
Revises: 0029_evenement_liens
Create Date: 2026-07-01
"""
# ruff: noqa: E501
from __future__ import annotations

from alembic import op

revision = "0030_notif_workflow"
down_revision = "0029_evenement_liens"
branch_labels = None
depends_on = None

_TYPES = [
    ("inscription_soumise", "Dossier d'adhésion reçu", "inscription", True, False),
    ("engagement_code", "Code de signature électronique", "inscription", True, False),
    ("attestation_requise", "Attestation signée requise", "inscription", True, False),
    ("attestation_rappel", "Rappel attestation signée", "rappels", True, True),
    ("attestation_expiree", "Attestation non retournée", "inscription", True, False),
    ("correction_demandee", "Correction du dossier demandée", "inscription", True, False),
]

_TEMPLATES = [
    ("inscription_soumise",
     "Dossier d'adhésion bien reçu",
     "Bonjour {prenom}, nous confirmons la bonne réception de votre dossier d'adhésion. Il a été transmis à l'administration et sera étudié avec attention. Vous serez informé(e) de la suite par ce même canal. Merci de votre engagement.",
     "Membership application received",
     "Hello {prenom}, we confirm that your membership application has been received. It has been forwarded to the administration and will be reviewed carefully. You will be notified of the outcome through this channel. Thank you for your commitment."),
    ("engagement_code",
     "Votre code de signature électronique",
     "Bonjour {prenom}, voici votre code de signature électronique : {code}. Saisissez-le dans l'application pour valider votre lecture et votre acceptation des documents. Il est valable quelques minutes et strictement personnel.",
     "Your electronic signature code",
     "Hello {prenom}, here is your electronic signature code: {code}. Enter it in the app to confirm you have read and accepted the documents. It is valid for a few minutes and strictly personal."),
    ("attestation_requise",
     "Attestation signée à retourner",
     "Bonjour {prenom}, votre adhésion est validée. Conformément à la réglementation applicable dans votre pays, une attestation d'engagement signée de votre main est requise. Téléchargez-la dans votre espace, signez-la, puis renvoyez-la via l'application avant le {echeance}.",
     "Signed attestation to return",
     "Hello {prenom}, your membership is approved. In accordance with the regulations applicable in your country, a hand-signed commitment attestation is required. Download it in your space, sign it, and return it through the app before {echeance}."),
    ("attestation_rappel",
     "Rappel : attestation signée à retourner",
     "Bonjour {prenom}, il vous reste peu de temps pour retourner votre attestation d'engagement signée (échéance : {echeance}). Merci de la déposer dans l'application pour finaliser votre dossier.",
     "Reminder: signed attestation to return",
     "Hello {prenom}, there is little time left to return your signed commitment attestation (deadline: {echeance}). Please upload it in the app to finalize your file."),
    ("attestation_expiree",
     "Attestation non retournée : dossier suspendu",
     "Bonjour {prenom}, l'attestation d'engagement signée n'a pas été reçue dans le délai imparti. Votre dossier est suspendu. Contactez l'administration pour régulariser votre situation.",
     "Attestation not returned: file suspended",
     "Hello {prenom}, the signed commitment attestation was not received within the deadline. Your file is suspended. Please contact the administration to regularize your situation."),
    ("correction_demandee",
     "Votre dossier nécessite une correction",
     "Bonjour {prenom}, l'administration vous demande de corriger votre dossier d'adhésion. Motif : {motif}. Vos informations sont conservées : rouvrez votre dossier dans l'application, corrigez uniquement ce qui est demandé, puis renvoyez-le. Merci.",
     "Your file needs a correction",
     "Hello {prenom}, the administration asks you to correct your membership file. Reason: {motif}. Your information is kept: reopen your file in the app, correct only what is requested, and resubmit. Thank you."),
]


def upgrade() -> None:
    for cle, libelle, categorie, actif, scheduled in _TYPES:
        op.execute(
            "INSERT INTO type_notification (cle, libelle, categorie, actif, scheduled) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (cle) DO NOTHING",
            (cle, libelle, categorie, actif, scheduled),
        )
    for cle, titre, corps, titre_en, corps_en in _TEMPLATES:
        op.execute(
            "INSERT INTO modele_message (cle, titre, corps, titre_en, corps_en, categorie) VALUES (%s, %s, %s, %s, %s, 'inscription') ON CONFLICT (cle) DO NOTHING",
            (cle, titre, corps, titre_en, corps_en),
        )


def downgrade() -> None:
    for cle, *_ in _TEMPLATES:
        op.execute("DELETE FROM modele_message WHERE cle = %s", (cle,))
    for cle, *_ in _TYPES:
        op.execute("DELETE FROM type_notification WHERE cle = %s", (cle,))
