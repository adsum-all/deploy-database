# ruff: noqa: E501 - migrations carry long SQL lines
"""Instruction workflow on the moderator channel.

A channel subject is an instruction. It now carries a readable reference
(INS-YYYY-NNNNNN), a workflow stage, who took it in charge, which workspace it was
assigned to, its final restitution (report + short summary) and its closure. A
sequence backs the atomic, gap-tolerant numbering. Existing rows are backfilled to
the 'recue' stage; the status column is kept for backward compatibility.

Revision ID: 0121_canal_workflow
Revises: 0120_telegram_espace_intake
Create Date: 2026-07-11
"""
from __future__ import annotations

from alembic import op

revision = "0121_canal_workflow"
down_revision = "0120_telegram_espace_intake"
branch_labels = None
depends_on = None

_ETAPES = (
    "recue", "transcrite", "redigee", "a_qualifier", "prise_en_charge",
    "affectee", "chargee", "en_traitement", "traitee", "restituee", "a_verifier", "cloturee",
)


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS seq_instruction")
    etapes_sql = ", ".join(f"'{e}'" for e in _ETAPES)
    op.execute("ALTER TABLE collab_canal_message ADD COLUMN IF NOT EXISTS matricule text")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_canal_message_matricule ON collab_canal_message (matricule) WHERE matricule IS NOT NULL")
    op.execute("ALTER TABLE collab_canal_message ADD COLUMN IF NOT EXISTS prise_en_charge_par uuid REFERENCES utilisateur(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE collab_canal_message ADD COLUMN IF NOT EXISTS prise_en_charge_le timestamptz")
    op.execute("ALTER TABLE collab_canal_message ADD COLUMN IF NOT EXISTS assigne_espace_id uuid REFERENCES collab_espace(id) ON DELETE SET NULL")
    op.execute(f"ALTER TABLE collab_canal_message ADD COLUMN IF NOT EXISTS etape text NOT NULL DEFAULT 'recue' CHECK (etape IN ({etapes_sql}))")
    op.execute("ALTER TABLE collab_canal_message ADD COLUMN IF NOT EXISTS restitution_rapport text")
    op.execute("ALTER TABLE collab_canal_message ADD COLUMN IF NOT EXISTS restitution_resume text")
    op.execute("ALTER TABLE collab_canal_message ADD COLUMN IF NOT EXISTS cloture_le timestamptz")
    op.execute("ALTER TABLE collab_canal_message ADD COLUMN IF NOT EXISTS cloture_par uuid REFERENCES utilisateur(id) ON DELETE SET NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_canal_message_etape ON collab_canal_message (etape)")

    # Per-step history for the visual workflow: one row per transition, with who
    # and when. Read/write follow the collab channel role-sets (see 0116).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collab_canal_etape (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            message_id uuid NOT NULL REFERENCES collab_canal_message(id) ON DELETE CASCADE,
            etape text NOT NULL,
            acteur_id uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            detail text,
            cree_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_canal_etape_message ON collab_canal_etape (message_id, cree_le)")
    op.execute("ALTER TABLE collab_canal_etape ENABLE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY collab_canal_etape_select ON collab_canal_etape FOR SELECT USING (adsum_current_role() = ANY(ARRAY['super_admin', 'admin', 'gestionnaire', 'direction']::text[]))")
    op.execute("CREATE POLICY collab_canal_etape_write ON collab_canal_etape FOR ALL USING (adsum_current_role() = ANY(ARRAY['super_admin', 'admin', 'gestionnaire']::text[])) WITH CHECK (adsum_current_role() = ANY(ARRAY['super_admin', 'admin', 'gestionnaire']::text[]))")

    # Multiple assignees per instruction (a series of people). The single
    # assigne_id column is kept as the primary assignee for compatibility.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collab_canal_assignation (
            message_id uuid NOT NULL REFERENCES collab_canal_message(id) ON DELETE CASCADE,
            utilisateur_id uuid NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE,
            assigne_le timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (message_id, utilisateur_id)
        )
        """
    )
    op.execute("ALTER TABLE collab_canal_assignation ENABLE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY collab_canal_assignation_select ON collab_canal_assignation FOR SELECT USING (adsum_current_role() = ANY(ARRAY['super_admin', 'admin', 'gestionnaire', 'direction']::text[]))")
    op.execute("CREATE POLICY collab_canal_assignation_write ON collab_canal_assignation FOR ALL USING (adsum_current_role() = ANY(ARRAY['super_admin', 'admin', 'gestionnaire']::text[])) WITH CHECK (adsum_current_role() = ANY(ARRAY['super_admin', 'admin', 'gestionnaire']::text[]))")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS collab_canal_assignation")
    op.execute("DROP TABLE IF EXISTS collab_canal_etape")
    for col in ("cloture_par", "cloture_le", "restitution_resume", "restitution_rapport", "etape",
                "assigne_espace_id", "prise_en_charge_le", "prise_en_charge_par", "matricule"):
        op.execute(f"ALTER TABLE collab_canal_message DROP COLUMN IF EXISTS {col}")
    op.execute("DROP SEQUENCE IF EXISTS seq_instruction")
