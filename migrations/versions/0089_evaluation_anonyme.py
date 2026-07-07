"""Make the attendance-survey rating and comment strongly anonymous.

The attendance survey ("sondage de pointage") let a member confirm presence AND
leave a rating (1..5) and a free comment. These were stored as ``participation.note``
and ``participation.avis`` on the SAME row as the presence proof, keyed by member.
So a plain ``SELECT membre_id, note, avis FROM participation`` attributed every
rating and comment to a person: a direct privacy violation.

This migration splits the two purposes irreversibly, keeping presence
identifiable while making the evaluation anonymous by design:

- ``participation`` keeps the presence (member-keyed, identifiable) but LOSES the
  ``note`` and ``avis`` columns.
- ``evaluation_activite`` (content, NO membre_id): the rating and comment with
  only a coarse date, unlinkable to a person.
- ``evaluation_activite_droit`` (membre-keyed, NO content): records that a member
  used their one-time right to evaluate. Prevents duplicates, proves nothing
  about the content.

Existing ratings/comments are moved into the anonymous table (dropping the member
link) and the consumption is backfilled, then the nominative columns are dropped.
Irreversible on purpose: the attribution must not be recoverable.

Revision ID: 0089_evaluation_anonyme
Revises: 0088_questionnaire_anonyme
"""
from __future__ import annotations

from alembic import op

revision = "0089_evaluation_anonyme"
down_revision = "0088_questionnaire_anonyme"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Anonymous content: rating + comment, NO member link, coarse date only.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS evaluation_activite (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            evenement_id uuid NOT NULL REFERENCES evenement(id) ON DELETE CASCADE,
            note smallint CHECK (note IS NULL OR (note BETWEEN 1 AND 5)),
            avis text,
            jour date NOT NULL DEFAULT current_date
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_evaluation_activite_ev ON evaluation_activite (evenement_id)")
    op.execute("ALTER TABLE evaluation_activite ENABLE ROW LEVEL SECURITY")

    # Member-side one-time consumption, NO content.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS evaluation_activite_droit (
            evenement_id uuid NOT NULL REFERENCES evenement(id) ON DELETE CASCADE,
            membre_id uuid NOT NULL REFERENCES membre(id) ON DELETE CASCADE,
            a_evalue boolean NOT NULL DEFAULT true,
            PRIMARY KEY (evenement_id, membre_id)
        )
        """
    )
    op.execute("ALTER TABLE evaluation_activite_droit ENABLE ROW LEVEL SECURITY")

    # Move existing ratings/comments into the anonymous table (drop the member link),
    # coarsening the timestamp to a date.
    op.execute(
        """
        INSERT INTO evaluation_activite (evenement_id, note, avis, jour)
        SELECT evenement_id, note, avis, coalesce(maj_le, cree_le, now())::date
        FROM participation
        WHERE note IS NOT NULL OR (avis IS NOT NULL AND btrim(avis) <> '')
        """
    )
    # Backfill the consumption so a member who already evaluated cannot evaluate again.
    op.execute(
        """
        INSERT INTO evaluation_activite_droit (evenement_id, membre_id)
        SELECT DISTINCT evenement_id, membre_id
        FROM participation
        WHERE note IS NOT NULL OR (avis IS NOT NULL AND btrim(avis) <> '')
        ON CONFLICT DO NOTHING
        """
    )

    # Remove the nominative evaluation columns from the presence row.
    op.execute("ALTER TABLE participation DROP COLUMN IF EXISTS note")
    op.execute("ALTER TABLE participation DROP COLUMN IF EXISTS avis")


def downgrade() -> None:
    # The anonymisation is deliberately irreversible: the per-member attribution
    # was destroyed. This only rebuilds the (empty) columns and drops the new tables.
    op.execute("ALTER TABLE participation ADD COLUMN IF NOT EXISTS avis text")
    op.execute("ALTER TABLE participation ADD COLUMN IF NOT EXISTS note integer")
    op.execute("DROP TABLE IF EXISTS evaluation_activite_droit")
    op.execute("DROP TABLE IF EXISTS evaluation_activite")
