"""Collaboration access-request notification: one governed type and its bilingual
template, so a space owner/admin is told off-channel when someone asks to join a
space (in addition to the in-app notification).

Additive only: seeds type_notification and modele_message for 'collab_demande'.
No existing flow is changed.

Revision ID: 0101_collab_demande_notif
Revises: 0100_collab_notif_catalogue
"""
from __future__ import annotations

from alembic import op

revision = "0101_collab_demande_notif"
down_revision = "0100_collab_notif_catalogue"
branch_labels = None
depends_on = None

CLE = "collab_demande"


def upgrade() -> None:
    op.execute(
        "INSERT INTO type_notification (cle, libelle, categorie, actif, scheduled, sensibilite) "
        "VALUES (%s, 'Collaboration: demande d''acces a un espace', 'collaboration', true, false, 'operationnel') "
        "ON CONFLICT (cle) DO UPDATE SET libelle = EXCLUDED.libelle, categorie = EXCLUDED.categorie",
        (CLE,),
    )
    # Placeholders: {prenom} (recipient owner/admin), {demandeur}, {espace}.
    op.execute(
        "INSERT INTO modele_message (cle, titre, corps, titre_en, corps_en, categorie) "
        "VALUES (%s, %s, %s, %s, %s, 'collaboration') ON CONFLICT (cle) DO NOTHING",
        (
            CLE,
            "Nouvelle demande d'acces",
            "Bonjour {prenom}, {demandeur} demande a rejoindre l'espace {espace}.",
            "New access request",
            "Hello {prenom}, {demandeur} is requesting to join the space {espace}.",
        ),
    )


def downgrade() -> None:
    op.execute("DELETE FROM modele_message WHERE cle = %s", (CLE,))
    op.execute("DELETE FROM type_notification WHERE cle = %s", (CLE,))
