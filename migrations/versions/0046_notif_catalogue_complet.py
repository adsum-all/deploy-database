# ruff: noqa: E501 - migrations carry long SQL and seeded text lines
"""Complete the member notification catalog and add the sensitivity levels.

Adds the remaining notification types (account blocked/unblocked, unusual login,
security alert, activity cancelled, attendance form closing soon, expired code,
modification needs more information) with bilingual, accented, professional and
respectful templates. Also stores a per-type sensitivity level on
type_notification so the engine can enforce channel rules (critical security
messages are never suppressed by a preference or a channel kill-switch).

Revision ID: 0046_notif_catalogue_complet
Revises: 0045_evenement_titres_accents
Create Date: 2026-07-03
"""
from __future__ import annotations

from alembic import op

revision = "0046_notif_catalogue_complet"
down_revision = "0045_evenement_titres_accents"
branch_labels = None
depends_on = None

# (cle, libelle, categorie, actif, scheduled, sensibilite)
_TYPES = [
    ("compte_bloque", "Compte suspendu", "securite", True, False, "prive"),
    ("compte_debloque", "Compte reactive", "securite", True, False, "prive"),
    ("connexion_inhabituelle", "Connexion inhabituelle", "securite", True, False, "critique"),
    ("securite_alerte", "Alerte de securite", "securite", True, False, "critique"),
    ("activite_annulee", "Activite annulee", "evenement", True, False, "operationnel"),
    ("participation_bientot_close", "Formulaire de presence bientot clos", "activite", True, True, "operationnel"),
    ("otp_expire", "Code expire", "transactionnel", True, False, "critique"),
    ("modification_complement", "Complement demande", "transactionnel", True, False, "prive"),
]

# (cle, titre_fr, corps_fr, titre_en, corps_en)
_TEMPLATES = [
    ("compte_bloque",
     "Votre compte a ete suspendu",
     "Bonjour {prenom}, votre compte ADSUM a ete temporairement suspendu par l'administration. Motif : {motif}. Pour toute question ou pour regulariser votre situation, contactez l'administration.",
     "Your account has been suspended",
     "Hello {prenom}, your ADSUM account has been temporarily suspended by the administration. Reason: {motif}. For any question or to resolve your situation, please contact the administration."),
    ("compte_debloque",
     "Votre compte a ete reactive",
     "Bonjour {prenom}, votre compte ADSUM a ete reactive. Vous pouvez de nouveau vous connecter et acceder a votre espace membre. Que le Seigneur vous garde.",
     "Your account has been reactivated",
     "Hello {prenom}, your ADSUM account has been reactivated. You can sign in again and access your member space. May the Lord keep you."),
    ("connexion_inhabituelle",
     "Nouvelle connexion a votre compte",
     "Bonjour {prenom}, une connexion a votre compte ADSUM a ete effectuee depuis un appareil que nous ne reconnaissons pas. Si c'etait bien vous, ignorez ce message. Sinon, changez votre mot de passe sans tarder et prevenez l'administration.",
     "New sign-in to your account",
     "Hello {prenom}, a sign-in to your ADSUM account was made from a device we do not recognise. If this was you, ignore this message. Otherwise, change your password right away and notify the administration."),
    ("securite_alerte",
     "Alerte de securite sur votre compte",
     "Bonjour {prenom}, une activite inhabituelle a ete detectee sur votre compte. Par precaution, verifiez vos informations et changez votre mot de passe. En cas de doute, contactez l'administration.",
     "Security alert on your account",
     "Hello {prenom}, unusual activity was detected on your account. As a precaution, review your information and change your password. If in doubt, contact the administration."),
    ("activite_annulee",
     "Activite annulee : {titre}",
     "Bonjour {prenom}, l'activite « {titre} » prevue le {date} est annulee. Nous vous tiendrons informe de toute reprogrammation. Merci de votre comprehension.",
     "Activity cancelled: {titre}",
     "Hello {prenom}, the activity « {titre} » scheduled for {date} has been cancelled. We will let you know of any rescheduling. Thank you for your understanding."),
    ("participation_bientot_close",
     "Derniere chance : formulaire de presence",
     "Bonjour {prenom}, le formulaire de presence pour « {titre} » se ferme bientot. Si vous avez participe, prenez un instant pour confirmer votre presence dans l'application : {lien}.",
     "Last chance: attendance form",
     "Hello {prenom}, the attendance form for « {titre} » is closing soon. If you took part, take a moment to confirm your attendance in the app: {lien}."),
    ("otp_expire",
     "Votre code de verification a expire",
     "Bonjour {prenom}, le code de verification demande a expire ou a deja ete utilise. Pour continuer, demandez un nouveau code depuis l'application. Ne communiquez jamais vos codes a personne.",
     "Your verification code has expired",
     "Hello {prenom}, the requested verification code has expired or was already used. To continue, request a new code from the app. Never share your codes with anyone."),
    ("modification_complement",
     "Complement d'information demande",
     "Bonjour {prenom}, pour traiter votre demande de modification, l'administration a besoin d'un complement : {motif}. Rouvrez votre demande dans l'application pour repondre et, si besoin, joindre une piece.",
     "Additional information requested",
     "Hello {prenom}, to process your modification request, the administration needs more information: {motif}. Reopen your request in the app to reply and, if needed, attach a document."),
]


def upgrade() -> None:
    op.execute("ALTER TABLE type_notification ADD COLUMN IF NOT EXISTS sensibilite text NOT NULL DEFAULT 'operationnel'")
    for cle, libelle, categorie, actif, scheduled, sens in _TYPES:
        op.execute(
            "INSERT INTO type_notification (cle, libelle, categorie, actif, scheduled, sensibilite) "
            "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (cle) DO UPDATE SET sensibilite = EXCLUDED.sensibilite",
            (cle, libelle, categorie, actif, scheduled, sens),
        )
    for cle, tf, cf, te, ce in _TEMPLATES:
        op.execute(
            "INSERT INTO modele_message (cle, titre, corps, titre_en, corps_en, categorie) "
            "VALUES (%s, %s, %s, %s, %s, 'securite') ON CONFLICT (cle) DO NOTHING",
            (cle, tf, cf, te, ce),
        )
    # Backfill the sensitivity of the pre-existing critical/private types.
    op.execute("UPDATE type_notification SET sensibilite = 'critique' WHERE cle IN ('otp', 'engagement_code')")
    op.execute(
        "UPDATE type_notification SET sensibilite = 'prive' WHERE cle IN "
        "('compte_cree', 'inscription_decision', 'inscription_soumise', 'modification_decision', "
        "'correction_demandee', 'attestation_requise', 'attestation_expiree', 'demande_reponse', 'document_demande')"
    )
    op.execute("UPDATE type_notification SET sensibilite = 'informationnel' WHERE cle IN ('annonce', 'agenda_hebdo', 'recap_hebdo', 'anniversaire', 'anniversaire_pairs')")


def downgrade() -> None:
    for cle, *_ in _TEMPLATES:
        op.execute("DELETE FROM modele_message WHERE cle = %s", (cle,))
    for cle, *_ in _TYPES:
        op.execute("DELETE FROM type_notification WHERE cle = %s", (cle,))
    op.execute("ALTER TABLE type_notification DROP COLUMN IF EXISTS sensibilite")
