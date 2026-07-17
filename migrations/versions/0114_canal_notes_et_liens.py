"""Moderator channel: several voice notes per channel, and links between channels.

Until now a channel (collab_canal_message) held a single voice note and one
two-level transcription. The moderator needs to reopen an existing channel and add
as many voice notes as needed, EACH with its own verbatim transcription and its own
professional redaction. Channels can also reference a parent channel to form an
organisational tree (continuity), ordered by date and priority.

This adds:
- collab_canal_note: one voice note inside a channel (its own transcription pair,
  status and audio-retention flag). Ordered by ``ordre`` then creation time.
- collab_piece.canal_note_id: the audio object of a note (a note's audio is a piece
  tied to the note; documents/images stay tied to the channel, note_id NULL).
- collab_canal_message.parent_id: optional link to another channel (continuity/tree).

Existing channels are migrated: each channel that already has an audio piece and/or a
transcription becomes a first note (ordre 0) carrying that transcription and audio, so
nothing is lost and the UI shows it as note 1.

Additive/backfill only. Revision ID: 0114_canal_notes_et_liens
Revises: 0113_preference_matrice_canaux
"""
from __future__ import annotations

from alembic import op

revision = "0114_canal_notes_et_liens"
down_revision = "0113_preference_matrice_canaux"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collab_canal_note (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            canal_message_id uuid NOT NULL REFERENCES collab_canal_message(id) ON DELETE CASCADE,
            ordre integer NOT NULL DEFAULT 0,
            transcription_brute text NOT NULL DEFAULT '',
            transcription_redigee text NOT NULL DEFAULT '',
            transcription_statut text NOT NULL DEFAULT 'aucune',
            transcription_erreur text,
            audio_conserver boolean NOT NULL DEFAULT false,
            cree_le timestamptz NOT NULL DEFAULT now(),
            maj_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_canal_note_message ON collab_canal_note (canal_message_id, ordre)")
    op.execute("ALTER TABLE collab_piece ADD COLUMN IF NOT EXISTS canal_note_id uuid")
    op.execute("CREATE INDEX IF NOT EXISTS ix_collab_piece_note ON collab_piece (canal_note_id)")
    op.execute("ALTER TABLE collab_canal_message ADD COLUMN IF NOT EXISTS parent_id uuid")
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'collab_canal_message_parent_fk') THEN "
        "ALTER TABLE collab_canal_message ADD CONSTRAINT collab_canal_message_parent_fk "
        "FOREIGN KEY (parent_id) REFERENCES collab_canal_message(id) ON DELETE SET NULL; "
        "END IF; END $$;"
    )

    # Backfill: turn each existing channel that has an audio piece or a transcription
    # into a first note (ordre 0), then attach its audio piece to that note.
    op.execute(
        """
        INSERT INTO collab_canal_note (canal_message_id, ordre, transcription_brute,
            transcription_redigee, transcription_statut, transcription_erreur, audio_conserver, cree_le)
        SELECT m.id, 0, coalesce(m.transcription_brute, ''), coalesce(m.transcription_redigee, ''),
               coalesce(m.transcription_statut, 'aucune'), m.transcription_erreur,
               coalesce(m.audio_conserver, false), m.cree_le
        FROM collab_canal_message m
        WHERE (
                EXISTS (SELECT 1 FROM collab_piece p WHERE p.canal_message_id = m.id AND p.est_audio)
             OR coalesce(m.transcription_brute, '') <> ''
             OR coalesce(m.transcription_redigee, '') <> ''
          )
          AND NOT EXISTS (SELECT 1 FROM collab_canal_note n WHERE n.canal_message_id = m.id)
        """
    )
    op.execute(
        """
        UPDATE collab_piece p SET canal_note_id = n.id
        FROM collab_canal_note n
        WHERE p.canal_message_id = n.canal_message_id AND n.ordre = 0 AND p.est_audio
          AND p.canal_note_id IS NULL
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE collab_canal_message DROP CONSTRAINT IF EXISTS collab_canal_message_parent_fk")
    op.execute("ALTER TABLE collab_canal_message DROP COLUMN IF EXISTS parent_id")
    op.execute("DROP INDEX IF EXISTS ix_collab_piece_note")
    op.execute("ALTER TABLE collab_piece DROP COLUMN IF EXISTS canal_note_id")
    op.execute("DROP TABLE IF EXISTS collab_canal_note")
