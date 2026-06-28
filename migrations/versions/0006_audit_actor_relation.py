"""Relate the audit table to utilisateur, removing the only isolated table (I3).

The DAT relations section declares "utilisateur 1 to N audit" (the actor of each
sensitive action), but the audit DDL omitted the foreign key, which left audit
isolated (no incoming nor outgoing relation). This migration adds the relation on
audit.acteur_id with ON DELETE NO ACTION, so every one of the 18 tables now
participates in a coherent relation of the model (Constitution I3, no orphan, no
isolated table). NO ACTION preserves the append-only nature of audit: staff users
are soft deleted (utilisateur.actif), so the constraint never fires and never
modifies an audit row. See ADR-0003.

Revision ID: 0006_audit_actor_relation
Revises: 0005_rls_role_policies
Create Date: 2026-06-28
"""
from __future__ import annotations

from alembic import op

revision = "0006_audit_actor_relation"
down_revision = "0005_rls_role_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE audit ADD CONSTRAINT fk_audit_acteur "
        "FOREIGN KEY (acteur_id) REFERENCES utilisateur(id) ON DELETE NO ACTION"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE audit DROP CONSTRAINT IF EXISTS fk_audit_acteur")
