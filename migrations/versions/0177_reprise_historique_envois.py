# ruff: noqa: E501 - migrations carry long SQL lines
"""Rebuild the send history from the audit journal, so the ledger is not born blind.

The outbox starts empty, which makes every past registration look as though nothing
was ever sent, including the people who demonstrably received and opened their
invitation. A repair screen that accuses the platform of never writing to somebody is
worse than no screen: it sends an administrator chasing a problem that does not exist,
and hides the ones that do.

The audit journal already recorded each creation and each resend, with the verdict the
provider gave at the time. That is imported here as the history it is: an accepted
request, not a proven delivery. The status is therefore 'envoye' and never 'delivre',
because the journal cannot testify to what happened afterwards.

Revision ID: 0177_reprise_historique_envois
Revises: 0176_registre_envois_email
Create Date: 2026-07-26
"""
from __future__ import annotations

from alembic import op

revision = "0177_reprise_historique_envois"
down_revision = "0176_registre_envois_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # One outbox row per past invitation, taken from what the journal recorded. The
    # idempotency key is left NULL: these are historical facts, not requests that
    # could be replayed, and a future genuine send must not collide with them.
    op.execute(
        """
        INSERT INTO email_outbox
            (membre_id, destinataire, template_code, sujet, statut, fournisseur,
             erreur, tentatives, contexte, priorite, cree_le, envoye_le)
        SELECT
            a.objet_id,
            m.email,
            'invitation_mot_de_passe_temporaire',
            'ADSUM, votre accès et mot de passe temporaire',
            CASE WHEN coalesce((a.details ->> 'email_envoye')::boolean, false)
                 THEN 'envoye' ELSE 'echoue' END,
            a.details ->> 'canal',
            CASE WHEN coalesce((a.details ->> 'email_envoye')::boolean, false)
                 THEN NULL ELSE 'aucun canal n''a accepté le message' END,
            1,
            jsonb_build_object('repris_du_journal', true, 'action', a.action),
            'critique',
            a.horodatage,
            CASE WHEN coalesce((a.details ->> 'email_envoye')::boolean, false)
                 THEN a.horodatage ELSE NULL END
        FROM audit a
        JOIN membre m ON m.id = a.objet_id
        WHERE a.action IN ('creation_inscription', 'relance_mdp_temporaire')
          AND a.objet_type = 'membre'
          AND m.email IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM email_outbox o
              WHERE o.membre_id = a.objet_id
                AND o.cree_le = a.horodatage
                AND o.template_code = 'invitation_mot_de_passe_temporaire'
          )
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM email_outbox WHERE contexte ->> 'repris_du_journal' = 'true'")
