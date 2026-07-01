"""Member participation per activity and Telegram as the default channel.

Beyond in-person QR check-ins, a member can declare how they took part in an
activity, especially online: present, partial ("suivi partiel") or absent. A
single row per member and event guarantees no double counting; a QR scan wins
and locks the presence, while an online declaration is only counted once the
member validates it. Feedback (opinion + rating) is open to everyone.

Telegram is the only free channel, so it becomes opt-in by default.

Revision ID: 0023_participation
Revises: 0022_intl_birthday_channels
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0023_participation"
down_revision = "0022_intl_birthday_channels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS participation (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            evenement_id uuid NOT NULL REFERENCES evenement(id) ON DELETE CASCADE,
            membre_id uuid NOT NULL REFERENCES membre(id) ON DELETE CASCADE,
            statut text NOT NULL CHECK (statut IN ('present', 'partiel', 'absent')),
            source text NOT NULL DEFAULT 'declaration' CHECK (source IN ('scan', 'declaration')),
            valide boolean NOT NULL DEFAULT false,
            avis text,
            note integer CHECK (note IS NULL OR (note BETWEEN 1 AND 5)),
            cree_le timestamptz NOT NULL DEFAULT now(),
            maj_le timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT participation_uq UNIQUE (evenement_id, membre_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_participation_evenement ON participation (evenement_id, statut)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_participation_membre ON participation (membre_id)")

    # Backfill: every existing QR check-in is a validated in-person presence.
    op.execute(
        """
        INSERT INTO participation (evenement_id, membre_id, statut, source, valide)
        SELECT evenement_id, membre_id, 'present', 'scan', true FROM presence
        ON CONFLICT (evenement_id, membre_id) DO NOTHING
        """
    )

    # Telegram is the free channel: make it opt-in by default.
    op.execute("ALTER TABLE preference_notification ALTER COLUMN telegram SET DEFAULT true")
    op.execute("UPDATE preference_notification SET telegram = true WHERE telegram = false")


def downgrade() -> None:
    op.execute("ALTER TABLE preference_notification ALTER COLUMN telegram SET DEFAULT false")
    op.execute("DROP TABLE IF EXISTS participation")
