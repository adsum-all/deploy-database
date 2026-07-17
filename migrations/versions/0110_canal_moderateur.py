"""Moderator channel: voice-note driven instruction requests for the founder.

The moderator (one or two people) drops instruction requests, often as voice
notes, sometimes several at once. The collaboration team retrieves them here,
well categorised and prioritised. Each message carries a written note and/or an
audio note plus attachments, a two-level transcription (a verbatim raw text and a
professional redaction, both editable, faithful to the audio) and a reply thread.
A message can be turned into a real card.

Audio and attachments reuse ``collab_piece`` (private bucket, signed URLs): a new
``canal_message_id`` target column is added and the single-target CHECK is widened
to exactly one of card / comment / channel-message. ``est_audio`` marks the voice
note and ``duree_s`` stores its duration.

Additive only. Revision ID: 0110_canal_moderateur
Revises: 0109_ai_provider_config
"""
from __future__ import annotations

from alembic import op

revision = "0110_canal_moderateur"
down_revision = "0109_ai_provider_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collab_canal_message (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            auteur_id uuid NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE,
            espace_id uuid REFERENCES collab_espace(id) ON DELETE SET NULL,
            assigne_id uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            carte_id uuid REFERENCES collab_carte(id) ON DELETE SET NULL,
            categorie text NOT NULL DEFAULT 'autre'
                CHECK (categorie IN ('projet', 'activite', 'organisation', 'communication', 'urgence', 'autre')),
            priorite text NOT NULL DEFAULT 'normale'
                CHECK (priorite IN ('urgente', 'haute', 'normale', 'basse')),
            statut text NOT NULL DEFAULT 'nouveau'
                CHECK (statut IN ('nouveau', 'en_cours', 'traite', 'archive')),
            sujet text NOT NULL DEFAULT '',
            note text NOT NULL DEFAULT '',
            transcription_brute text NOT NULL DEFAULT '',
            transcription_redigee text NOT NULL DEFAULT '',
            transcription_statut text NOT NULL DEFAULT 'aucune'
                CHECK (transcription_statut IN ('aucune', 'en_cours', 'prete', 'echec')),
            transcription_erreur text,
            cree_le timestamptz NOT NULL DEFAULT now(),
            maj_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_canal_message_statut ON collab_canal_message(statut)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_canal_message_cree ON collab_canal_message(cree_le DESC)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collab_canal_reponse (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            message_id uuid NOT NULL REFERENCES collab_canal_message(id) ON DELETE CASCADE,
            auteur_id uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            corps text NOT NULL,
            cree_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_canal_reponse_msg ON collab_canal_reponse(message_id)")

    # Extend collab_piece to also target a channel message, and carry audio metadata.
    op.execute(
        "ALTER TABLE collab_piece ADD COLUMN IF NOT EXISTS canal_message_id uuid "
        "REFERENCES collab_canal_message(id) ON DELETE CASCADE"
    )
    op.execute("ALTER TABLE collab_piece ADD COLUMN IF NOT EXISTS est_audio boolean NOT NULL DEFAULT false")
    op.execute("ALTER TABLE collab_piece ADD COLUMN IF NOT EXISTS duree_s integer")
    op.execute("CREATE INDEX IF NOT EXISTS idx_collab_piece_canal ON collab_piece(canal_message_id)")

    # Widen the single-target CHECK to exactly one of card / comment / channel-message.
    op.execute("ALTER TABLE collab_piece DROP CONSTRAINT IF EXISTS collab_piece_cible")
    op.execute(
        "ALTER TABLE collab_piece ADD CONSTRAINT collab_piece_cible CHECK ("
        "(carte_id IS NOT NULL)::int + (commentaire_id IS NOT NULL)::int "
        "+ (canal_message_id IS NOT NULL)::int = 1)"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE collab_piece DROP CONSTRAINT IF EXISTS collab_piece_cible")
    op.execute("ALTER TABLE collab_piece DROP COLUMN IF EXISTS duree_s")
    op.execute("ALTER TABLE collab_piece DROP COLUMN IF EXISTS est_audio")
    op.execute("ALTER TABLE collab_piece DROP COLUMN IF EXISTS canal_message_id")
    op.execute(
        "ALTER TABLE collab_piece ADD CONSTRAINT collab_piece_cible CHECK ("
        "(carte_id IS NOT NULL)::int + (commentaire_id IS NOT NULL)::int = 1)"
    )
    op.execute("DROP TABLE IF EXISTS collab_canal_reponse")
    op.execute("DROP TABLE IF EXISTS collab_canal_message")
