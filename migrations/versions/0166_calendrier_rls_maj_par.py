# ruff: noqa: E501 - migrations carry long SQL lines
"""Reconcile the reference-date write RLS with the application gate, and trace the
liturgical catalogue actor.

The reference-date endpoints are gated by ``parametres.gerer`` (held by gestionnaire,
admin, super_admin), but the write RLS on ``date_institutionnelle`` (0160) and
``date_liturgique`` (0165) was restricted to admin/super_admin. Because the API
connects as the schema owner and bypasses RLS, the two layers disagreed on intent.
We align the defense-in-depth RLS to the real, intended enforcement: the roles that
hold ``parametres.gerer``. Also add ``maj_par`` to ``date_liturgique`` so catalogue
mutations record their actor, like the other reference tables.

Revision ID: 0166_calendrier_rls_maj_par
Revises: 0165_calendrier_institutionnel
Create Date: 2026-07-20
"""
from __future__ import annotations

from alembic import op

revision = "0166_calendrier_rls_maj_par"
down_revision = "0165_calendrier_institutionnel"
branch_labels = None
depends_on = None

_GERER = "ARRAY['super_admin', 'admin', 'gestionnaire']::text[]"
_ADMIN = "ARRAY['super_admin', 'admin']::text[]"


def upgrade() -> None:
    op.execute(f"ALTER POLICY date_institutionnelle_write ON date_institutionnelle USING (adsum_current_role() = ANY({_GERER})) WITH CHECK (adsum_current_role() = ANY({_GERER}))")
    op.execute(f"ALTER POLICY date_liturgique_write ON date_liturgique USING (adsum_current_role() = ANY({_GERER})) WITH CHECK (adsum_current_role() = ANY({_GERER}))")
    op.execute("ALTER TABLE date_liturgique ADD COLUMN IF NOT EXISTS maj_par uuid")


def downgrade() -> None:
    op.execute("ALTER TABLE date_liturgique DROP COLUMN IF EXISTS maj_par")
    op.execute(f"ALTER POLICY date_liturgique_write ON date_liturgique USING (adsum_current_role() = ANY({_ADMIN})) WITH CHECK (adsum_current_role() = ANY({_ADMIN}))")
    op.execute(f"ALTER POLICY date_institutionnelle_write ON date_institutionnelle USING (adsum_current_role() = ANY({_ADMIN})) WITH CHECK (adsum_current_role() = ANY({_ADMIN}))")
