"""Birthday directory: peer visibility, calendar overlay preferences and digest.

Adds the RGPD-safe controls that let members see each other's birthdays in the
calendar. A member can remove their own birthday from the peer directory
(independent of the birth-year visibility flag, which stays about the year only).
Calendar overlays default to VIP-on, responsables-off, own-commission-off, and a
daily "today's birthdays" digest is opt-in. The birth year is never exposed in
the peer directory regardless of the year flag.

Revision ID: 0027_anniversaire_annuaire
Revises: 0026_membre_fonction
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0027_anniversaire_annuaire"
down_revision = "0026_membre_fonction"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS anniversaire_visible_annuaire boolean NOT NULL DEFAULT true")
    # Overlay preferences: VIP birthdays on by default, responsables and own
    # commission off; the daily peer-birthday digest opt-in but on by default.
    op.execute("ALTER TABLE preference_notification ADD COLUMN IF NOT EXISTS anniv_pairs boolean NOT NULL DEFAULT true")
    op.execute("ALTER TABLE preference_notification ADD COLUMN IF NOT EXISTS cal_vip boolean NOT NULL DEFAULT true")
    op.execute("ALTER TABLE preference_notification ADD COLUMN IF NOT EXISTS cal_responsables boolean NOT NULL DEFAULT false")
    op.execute("ALTER TABLE preference_notification ADD COLUMN IF NOT EXISTS cal_commission boolean NOT NULL DEFAULT false")
    op.execute(
        "INSERT INTO type_notification (cle, libelle, categorie, actif, scheduled) "
        "VALUES (%s, %s, %s, true, true) ON CONFLICT (cle) DO NOTHING",
        ("anniversaire_pairs", "Anniversaires du jour", "communaute"),
    )
    op.execute(
        "INSERT INTO modele_message (cle, titre, corps, titre_en, corps_en, categorie) "
        "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (cle) DO NOTHING",
        (
            "anniversaire_pairs",
            "Anniversaires du jour",
            "Aujourd'hui, nous célébrons : {liste}. Prenez un instant pour adresser vos vœux fraternels.",
            "Today's birthdays",
            "Today we celebrate: {liste}. Take a moment to send your warm wishes.",
            "communaute",
        ),
    )


def downgrade() -> None:
    op.execute("DELETE FROM modele_message WHERE cle = 'anniversaire_pairs'")
    op.execute("DELETE FROM type_notification WHERE cle = 'anniversaire_pairs'")
    op.execute("ALTER TABLE preference_notification DROP COLUMN IF EXISTS cal_commission")
    op.execute("ALTER TABLE preference_notification DROP COLUMN IF EXISTS cal_responsables")
    op.execute("ALTER TABLE preference_notification DROP COLUMN IF EXISTS cal_vip")
    op.execute("ALTER TABLE preference_notification DROP COLUMN IF EXISTS anniv_pairs")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS anniversaire_visible_annuaire")
