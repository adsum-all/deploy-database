"""Response-window honesty and participation modality.

The admin window parameter (questionnaire_fenetre_heures, set to 5h in
production) was ignored by the participation form, which hardcoded a 2-day
window: forms stayed answerable days after a session. Add a per-event override
(fenetre_reponse_heures, nullable: falls back to the admin parameter, then 6h)
so the single window formula can honor the administration's setting.

Also separate modality from channel: presence proved by a member-QR scan is
'presentiel' (strong proof); a declared participation must carry its own
declared modality instead of being counted as online just because it came
through the app. Existing scan rows are backfilled; declared rows keep NULL
(modality unknown) rather than a fabricated value.

Revision ID: 0052_fenetre_modalite
Revises: 0051_purge_evenements_seed
Create Date: 2026-07-04
"""
from __future__ import annotations

from alembic import op

revision = "0052_fenetre_modalite"
down_revision = "0051_purge_evenements_seed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE evenement ADD COLUMN IF NOT EXISTS fenetre_reponse_heures integer")
    op.execute(
        "ALTER TABLE participation ADD COLUMN IF NOT EXISTS modalite text "
        "CHECK (modalite IN ('presentiel', 'en_ligne'))"
    )
    # A member-QR check-in is strong proof of on-site attendance.
    op.execute("UPDATE participation SET modalite = 'presentiel' WHERE source = 'scan' AND modalite IS NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE evenement DROP COLUMN IF EXISTS fenetre_reponse_heures")
    op.execute("ALTER TABLE participation DROP COLUMN IF EXISTS modalite")
