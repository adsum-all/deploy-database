"""Audio retention for the moderator channel: keep voice notes 30 days by default.

A voice note is a raw recording; its value once transcribed is the text, not the
audio. To bound storage (RGPD data minimisation) the audio object is purged 30 days
after upload by the daily job, WHILE the transcription and every other element of
the message are kept for good. A moderator can opt a message out of the purge
(``audio_conserver = true``) to keep its audio indefinitely.

Additive only. Revision ID: 0111_canal_audio_retention
Revises: 0110_canal_moderateur
"""
from __future__ import annotations

from alembic import op

revision = "0111_canal_audio_retention"
down_revision = "0110_canal_moderateur"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE collab_canal_message ADD COLUMN IF NOT EXISTS audio_conserver boolean NOT NULL DEFAULT false"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE collab_canal_message DROP COLUMN IF EXISTS audio_conserver")
