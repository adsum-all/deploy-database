# ruff: noqa: E501 - migrations carry long SQL lines
"""Enable row level security on the identifier counter tables.

0054 added matricule_compteur and demande_compteur (year-partitioned atomic
counters). They hold no personal data, only a year and a sequence, but the
Constitution requires row level security on every table (RLS 100%). The API
connects as the database owner, which bypasses RLS, so no policy is needed for it
to keep bumping the counters; anon and authenticated were already revoked by
0042's default privileges. This migration only turns RLS on for the two tables.

Revision ID: 0055_rls_compteurs
Revises: 0054_soumission_ids
Create Date: 2026-07-04
"""
from __future__ import annotations

from alembic import op

revision = "0055_rls_compteurs"
down_revision = "0054_soumission_ids"
branch_labels = None
depends_on = None

_COUNTERS = ("matricule_compteur", "demande_compteur")


def upgrade() -> None:
    for table in _COUNTERS:
        op.execute(f'ALTER TABLE IF EXISTS public."{table}" ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    for table in _COUNTERS:
        op.execute(f'ALTER TABLE IF EXISTS public."{table}" DISABLE ROW LEVEL SECURITY')
