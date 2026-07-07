"""Make the end-of-activity questionnaire answers strongly anonymous.

Privacy-by-design requirement: the system must keep knowing WHO attended an
activity (presence stays in ``participation``, identifiable), but the RATING and
the free COMMENT of the end-of-activity questionnaire must never be attributable
to a member, directly or indirectly.

Before this migration ``reponse_questionnaire`` carried ``membre_id`` next to the
answers and a precise ``soumis_le`` timestamp, and the admin endpoint exposed the
member name and matricule with each answer. This migration splits the two
purposes irreversibly:

- ``questionnaire_droit`` (membre-keyed, NO content): records that a member has
  used their one-time right to answer. Prevents duplicates, proves nothing about
  what was answered.
- ``reponse_questionnaire`` (content only, NO membre_id): keeps only the answers
  and a COARSE date (``jour``), so nothing links a note/comment to a person, and
  no precise timestamp can be correlated with the consumption record.

The existing consumption state is backfilled so no member loses their "already
answered" status, and the precise time is coarsened to a date. Dropping
``membre_id`` is irreversible on purpose: the attribution must not be
recoverable.

Revision ID: 0088_questionnaire_anonyme
Revises: 0087_cal_categories_unite
"""
from __future__ import annotations

from alembic import op

revision = "0088_questionnaire_anonyme"
down_revision = "0087_cal_categories_unite"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Member-side one-time consumption record, WITHOUT any answer content.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS questionnaire_droit (
            questionnaire_id uuid NOT NULL REFERENCES questionnaire(id) ON DELETE CASCADE,
            membre_id uuid NOT NULL REFERENCES membre(id) ON DELETE CASCADE,
            a_repondu boolean NOT NULL DEFAULT true,
            PRIMARY KEY (questionnaire_id, membre_id)
        )
        """
    )
    op.execute("ALTER TABLE questionnaire_droit ENABLE ROW LEVEL SECURITY")

    # 2. Backfill the consumption record from the existing (nominative) answers so
    #    a member who already answered keeps their "already answered" state.
    op.execute(
        """
        INSERT INTO questionnaire_droit (questionnaire_id, membre_id)
        SELECT DISTINCT questionnaire_id, membre_id FROM reponse_questionnaire
        ON CONFLICT DO NOTHING
        """
    )

    # 3. Coarsen the timestamp to a date on the content table (a precise instant
    #    would let an admin correlate a consumption time with an answer).
    op.execute("ALTER TABLE reponse_questionnaire ADD COLUMN IF NOT EXISTS jour date")
    op.execute("UPDATE reponse_questionnaire SET jour = soumis_le::date WHERE jour IS NULL")

    # 4. Irreversibly break the link to the member: drop the uniqueness on member,
    #    the member_id column (and its FK), and the precise timestamp.
    op.execute("ALTER TABLE reponse_questionnaire DROP CONSTRAINT IF EXISTS reponse_questionnaire_uq")
    op.execute("ALTER TABLE reponse_questionnaire DROP COLUMN IF EXISTS membre_id")
    op.execute("ALTER TABLE reponse_questionnaire DROP COLUMN IF EXISTS soumis_le")
    op.execute("UPDATE reponse_questionnaire SET jour = current_date WHERE jour IS NULL")
    op.execute("ALTER TABLE reponse_questionnaire ALTER COLUMN jour SET DEFAULT current_date")
    op.execute("ALTER TABLE reponse_questionnaire ALTER COLUMN jour SET NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_reponse_questionnaire_q ON reponse_questionnaire (questionnaire_id)")


def downgrade() -> None:
    # The anonymisation is deliberately irreversible: the per-member attribution
    # was destroyed and cannot be restored. This only rebuilds the columns (empty)
    # and drops the consumption table so the chain can be stepped back structurally.
    op.execute("ALTER TABLE reponse_questionnaire ADD COLUMN IF NOT EXISTS membre_id uuid")
    op.execute("ALTER TABLE reponse_questionnaire ADD COLUMN IF NOT EXISTS soumis_le timestamptz DEFAULT now()")
    op.execute("DROP TABLE IF EXISTS questionnaire_droit")
