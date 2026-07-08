"""Collaboration notification catalogue: governed types, bilingual templates and a
member preference category, so collaboration notifications can flow through the
real multichannel engine (in-app + email + Telegram + WhatsApp).

Additive only: it seeds the catalogue (type_notification), the messages
(modele_message) and adds one preference column. No existing flow is changed; this
unblocks wiring collaboration events to notifier() (lot 2) without governance gaps.

Revision ID: 0100_collab_notif_catalogue
Revises: 0099_collab_actor_fks
"""
from __future__ import annotations

from alembic import op

revision = "0100_collab_notif_catalogue"
down_revision = "0099_collab_actor_fks"
branch_labels = None
depends_on = None

# (cle, libelle, scheduled) - all collaboration category, operational sensitivity.
TYPES = (
    ("collab_mention", "Collaboration: mention dans une carte", False),
    ("collab_assignation", "Collaboration: carte assignée", False),
    ("collab_echeance", "Collaboration: rappel d'échéance de carte", True),
    ("collab_publication", "Collaboration: activité publiée", False),
)

# (cle, titre_fr, corps_fr, titre_en, corps_en). Placeholders: {prenom} {titre} {espace} {echeance}.
TEMPLATES = (
    (
        "collab_mention",
        "Mention dans une carte",
        "Bonjour {prenom}, vous etes mentionne dans la carte « {titre} » de l'espace {espace}.",
        "Mentioned in a card",
        "Hello {prenom}, you were mentioned in the card '{titre}' of the space {espace}.",
    ),
    (
        "collab_assignation",
        "Nouvelle carte assignée",
        "Bonjour {prenom}, la carte « {titre} » vous a ete assignee dans l'espace {espace}.",
        "New card assigned",
        "Hello {prenom}, the card '{titre}' has been assigned to you in the space {espace}.",
    ),
    (
        "collab_echeance",
        "Échéance d'une carte",
        "Bonjour {prenom}, la carte « {titre} » arrive a echeance {echeance}.",
        "Card due date",
        "Hello {prenom}, the card '{titre}' is due {echeance}.",
    ),
    (
        "collab_publication",
        "Activité publiée",
        "Bonjour {prenom}, l'activite « {titre} » a ete publiee et ajoutee a l'agenda.",
        "Activity published",
        "Hello {prenom}, the activity '{titre}' has been published and added to the agenda.",
    ),
)


def upgrade() -> None:
    op.execute(
        "ALTER TABLE preference_notification ADD COLUMN IF NOT EXISTS collaboration boolean NOT NULL DEFAULT true"
    )
    for cle, libelle, scheduled in TYPES:
        op.execute(
            "INSERT INTO type_notification (cle, libelle, categorie, actif, scheduled, sensibilite) "
            "VALUES (%s, %s, 'collaboration', true, %s, 'operationnel') "
            "ON CONFLICT (cle) DO UPDATE SET libelle = EXCLUDED.libelle, categorie = EXCLUDED.categorie",
            (cle, libelle, scheduled),
        )
    for cle, tf, cf, te, ce in TEMPLATES:
        op.execute(
            "INSERT INTO modele_message (cle, titre, corps, titre_en, corps_en, categorie) "
            "VALUES (%s, %s, %s, %s, %s, 'collaboration') ON CONFLICT (cle) DO NOTHING",
            (cle, tf, cf, te, ce),
        )


def downgrade() -> None:
    for cle, _libelle, _scheduled in TYPES:
        op.execute("DELETE FROM modele_message WHERE cle = %s", (cle,))
        op.execute("DELETE FROM type_notification WHERE cle = %s", (cle,))
    op.execute("ALTER TABLE preference_notification DROP COLUMN IF EXISTS collaboration")
