# ruff: noqa: E501 - migrations carry long SQL lines
"""Deduplication ledger for Telegram voice-note ingestion into the moderator channel.

Voice notes are pulled on demand from the bot via getUpdates (no webhook, so the
existing OTP and account-linking flows that also read getUpdates keep working).
Because getUpdates returns the same pending updates until they age out, a ledger
keyed on the Telegram file id makes the import idempotent: a file already turned
into a channel note is never ingested twice. It also records who was imported,
from which chat, and into which channel message/note, for traceability.

Revision ID: 0119_telegram_voice_ingest
Revises: 0118_doublon_documents
Create Date: 2026-07-11
"""
from __future__ import annotations

from alembic import op

revision = "0119_telegram_voice_ingest"
down_revision = "0118_doublon_documents"
branch_labels = None
depends_on = None

# Staff role-sets mirroring the collab_* channel tables (see 0116): read for the
# committee roles plus direction, write for the committee.
_LECTURE = "ARRAY['super_admin', 'admin', 'gestionnaire', 'direction']::text[]"
_COMITE = "ARRAY['super_admin', 'admin', 'gestionnaire']::text[]"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS telegram_voice_ingest (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            telegram_file_id text NOT NULL,
            telegram_update_id bigint,
            chat_id text NOT NULL,
            membre_id uuid REFERENCES membre(id) ON DELETE SET NULL,
            canal_message_id uuid REFERENCES collab_canal_message(id) ON DELETE CASCADE,
            canal_note_id uuid,
            importe_par uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            cree_le timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT telegram_voice_ingest_file_uq UNIQUE (telegram_file_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_telegram_voice_ingest_chat ON telegram_voice_ingest (chat_id, cree_le DESC)")
    op.execute("ALTER TABLE telegram_voice_ingest ENABLE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY telegram_voice_ingest_select ON telegram_voice_ingest FOR SELECT USING (adsum_current_role() = ANY({_LECTURE}))")
    op.execute(f"CREATE POLICY telegram_voice_ingest_write ON telegram_voice_ingest FOR ALL USING (adsum_current_role() = ANY({_COMITE})) WITH CHECK (adsum_current_role() = ANY({_COMITE}))")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS telegram_voice_ingest")
