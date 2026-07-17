# ruff: noqa: E501 - migrations carry long SQL lines
"""Align the evenement cible_type CHECK constraints with the real targeting model.

The application (schema CreateEvenement, activites engine and the back-office form) supports
eight target kinds: general, the four organisational units (coordination, commission,
intendance, tribu) and three unit-less audiences (bergers, responsables, liste). The two
database CHECK constraints only knew five of them, so creating an activity targeted at
"Les Bergers", "Les responsables" or an e-mail "liste" violated the constraint and the
INSERT raised, surfacing to the operator as a generic 500 on the create form.

Two fixes, matching the model exactly:
- evenement_cible_type_chk: allow the three missing kinds (bergers, responsables, liste).
- evenement_cible_pair_chk: a unit id is required only for the four unit kinds; general and
  the three unit-less audiences carry no cible_id (it stays NULL). The old rule wrongly
  required a cible_id for every non-general kind.

Data-safe: every existing row is either general (cible_id NULL) or a unit kind
(cible_id NOT NULL), so all current rows already satisfy the new constraints.

Revision ID: 0144_evenement_cible_types
Revises: 0143_liens_fk_manquants
Create Date: 2026-07-17
"""
from __future__ import annotations

from alembic import op

revision = "0144_evenement_cible_types"
down_revision = "0143_liens_fk_manquants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE evenement DROP CONSTRAINT IF EXISTS evenement_cible_type_chk")
    op.execute(
        "ALTER TABLE evenement ADD CONSTRAINT evenement_cible_type_chk CHECK "
        "(cible_type = ANY (ARRAY['general', 'coordination', 'commission', 'intendance', 'tribu', 'bergers', 'responsables', 'liste']))"
    )
    op.execute("ALTER TABLE evenement DROP CONSTRAINT IF EXISTS evenement_cible_pair_chk")
    op.execute(
        "ALTER TABLE evenement ADD CONSTRAINT evenement_cible_pair_chk CHECK "
        "((cible_type IN ('general', 'bergers', 'responsables', 'liste') AND cible_id IS NULL) "
        "OR (cible_type IN ('coordination', 'commission', 'intendance', 'tribu') AND cible_id IS NOT NULL))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE evenement DROP CONSTRAINT IF EXISTS evenement_cible_pair_chk")
    op.execute(
        "ALTER TABLE evenement ADD CONSTRAINT evenement_cible_pair_chk CHECK "
        "(((cible_type = 'general') AND (cible_id IS NULL)) OR ((cible_type <> 'general') AND (cible_id IS NOT NULL)))"
    )
    op.execute("ALTER TABLE evenement DROP CONSTRAINT IF EXISTS evenement_cible_type_chk")
    op.execute(
        "ALTER TABLE evenement ADD CONSTRAINT evenement_cible_type_chk CHECK "
        "(cible_type = ANY (ARRAY['general', 'coordination', 'commission', 'intendance', 'tribu']))"
    )
