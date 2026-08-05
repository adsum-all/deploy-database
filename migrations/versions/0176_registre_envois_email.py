# ruff: noqa: E501 - migrations carry long SQL lines
"""Keep a record of every e-mail the platform sends, and of what became of it.

Until now a send was judged on the provider returning a 2xx, and that verdict was
written into the audit line as ``email_envoye: true``. It says the request was
accepted, nothing more. One registrant has ``email_envoye: true`` in the journal and
no trace at all in the provider's log, and another has every message soft-bounced by
their mailbox provider: both looked like successes from inside the application.

The outbox records the intent, the attempt and the outcome, and the delivery events
record what the provider reported afterwards, so a bounce or a rejection stops being
invisible. The idempotency key is what makes a re-send safe: asking twice for the
same message to the same person for the same reason produces one e-mail, which is
what allows an administrator to press "resend" without fear.

Revision ID: 0176_registre_envois_email
Revises: 0175_templates_collaboration
Create Date: 2026-07-26
"""
from __future__ import annotations

from alembic import op

revision = "0176_registre_envois_email"
down_revision = "0175_templates_collaboration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS email_outbox (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            membre_id uuid REFERENCES membre(id) ON DELETE SET NULL,
            destinataire text NOT NULL,
            template_code text NOT NULL,
            langue text NOT NULL DEFAULT 'fr',
            sujet text NOT NULL,
            contexte jsonb NOT NULL DEFAULT '{}'::jsonb,
            priorite text NOT NULL DEFAULT 'normale',
            statut text NOT NULL DEFAULT 'prepare',
            fournisseur text,
            fournisseur_message_id text,
            erreur text,
            tentatives integer NOT NULL DEFAULT 0,
            cle_idempotence text,
            cree_par uuid,
            cree_le timestamptz NOT NULL DEFAULT now(),
            envoye_le timestamptz,
            delivre_le timestamptz,
            ouvert_le timestamptz,
            echoue_le timestamptz,
            prochaine_tentative_le timestamptz
        )
        """
    )
    op.execute(
        "ALTER TABLE email_outbox DROP CONSTRAINT IF EXISTS email_outbox_statut_check"
    )
    op.execute(
        "ALTER TABLE email_outbox ADD CONSTRAINT email_outbox_statut_check CHECK (statut IN "
        "('prepare', 'en_file', 'en_cours', 'envoye', 'delivre', 'ouvert', 'rebondi', "
        "'rejete', 'echoue', 'expire', 'annule'))"
    )
    op.execute(
        "ALTER TABLE email_outbox DROP CONSTRAINT IF EXISTS email_outbox_priorite_check"
    )
    op.execute(
        "ALTER TABLE email_outbox ADD CONSTRAINT email_outbox_priorite_check "
        "CHECK (priorite IN ('critique', 'haute', 'normale', 'basse'))"
    )
    # Asking twice for the same message, to the same person, for the same reason must
    # produce one e-mail. This is what lets an administrator press "resend" safely.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS email_outbox_idempotence_uniq "
        "ON email_outbox (cle_idempotence) WHERE cle_idempotence IS NOT NULL"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_email_outbox_membre ON email_outbox (membre_id, cree_le DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_email_outbox_statut ON email_outbox (statut, cree_le DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_email_outbox_template ON email_outbox (template_code, cree_le DESC)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS email_delivery_event (
            id bigserial PRIMARY KEY,
            email_outbox_id uuid REFERENCES email_outbox(id) ON DELETE CASCADE,
            destinataire text,
            evenement_fournisseur text NOT NULL,
            statut_normalise text NOT NULL,
            motif text,
            charge_brute jsonb,
            survenu_le timestamptz NOT NULL DEFAULT now(),
            cree_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_email_event_outbox ON email_delivery_event (email_outbox_id, survenu_le DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_email_event_destinataire ON email_delivery_event (destinataire, survenu_le DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS email_delivery_event")
    op.execute("DROP TABLE IF EXISTS email_outbox")
