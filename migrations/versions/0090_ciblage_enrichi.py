"""Enrich activity targeting: gender, age range, people categories, e-mail list.

Until now an activity targeted everyone (``cible_type = 'general'``) or one
organisational unit. This adds finer, composable targeting so an activity can
reach, for example, "the women of commission X aged 18-30", "the Bergers", "the
responsables", or an ad-hoc list of e-mail addresses.

- ``cible_type`` gains three values: ``bergers`` (members marked est_berger),
  ``responsables`` (members holding a key function), ``liste`` (an explicit
  e-mail list). The unit values (commission/intendance/coordination/tribu) stay.
- ``cible_genre`` (homme/femme), ``cible_age_min``, ``cible_age_max`` are optional
  REFINEMENTS that combine (AND) with any target type.
- ``cible_emails`` holds the ad-hoc list for ``cible_type = 'liste'``.

All new columns default to NULL, so every existing activity keeps its exact
current audience.

Revision ID: 0090_ciblage_enrichi
Revises: 0089_evaluation_anonyme
"""
from __future__ import annotations

from alembic import op

revision = "0090_ciblage_enrichi"
down_revision = "0089_evaluation_anonyme"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE evenement ADD COLUMN IF NOT EXISTS cible_genre text")
    op.execute("ALTER TABLE evenement ADD COLUMN IF NOT EXISTS cible_age_min integer")
    op.execute("ALTER TABLE evenement ADD COLUMN IF NOT EXISTS cible_age_max integer")
    op.execute("ALTER TABLE evenement ADD COLUMN IF NOT EXISTS cible_emails text[]")
    op.execute(
        "ALTER TABLE evenement ADD CONSTRAINT evenement_cible_genre_chk "
        "CHECK (cible_genre IS NULL OR cible_genre IN ('homme', 'femme'))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE evenement DROP CONSTRAINT IF EXISTS evenement_cible_genre_chk")
    op.execute("ALTER TABLE evenement DROP COLUMN IF EXISTS cible_emails")
    op.execute("ALTER TABLE evenement DROP COLUMN IF EXISTS cible_age_max")
    op.execute("ALTER TABLE evenement DROP COLUMN IF EXISTS cible_age_min")
    op.execute("ALTER TABLE evenement DROP COLUMN IF EXISTS cible_genre")
