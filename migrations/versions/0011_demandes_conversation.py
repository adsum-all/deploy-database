"""Member requests and conversation with the administration.

Adds ``demande`` (a member request: information change, question, complaint…) and
``demande_message`` (the conversation thread between the member and the staff),
plus ``champs_deverrouilles`` on the member so the administration can unlock the
specific fields a member is allowed to edit after a justified request. This is the
"contact your organisation" flow found in real institutional apps (bank, CAF…).

RLS: a member reads/writes their own requests and messages; committee/staff read
and answer all. (ADR-0002.)

Revision ID: 0011_demandes_conversation
Revises: 0010_member_documents
Create Date: 2026-06-30
"""
from __future__ import annotations

from alembic import op

revision = "0011_demandes_conversation"
down_revision = "0009_collaboration"
branch_labels = None
depends_on = None

STAFF = "ARRAY['super_admin', 'admin', 'gestionnaire']::text[]"
LECTURE = "ARRAY['super_admin', 'admin', 'gestionnaire', 'direction']::text[]"
TYPES = ("modification_info", "question", "reclamation", "autre")
STATUTS = ("ouverte", "en_cours", "resolue", "refusee")


def upgrade() -> None:
    type_chk = ", ".join(f"'{v}'" for v in TYPES)
    statut_chk = ", ".join(f"'{v}'" for v in STATUTS)
    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS demande (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            membre_id uuid NOT NULL REFERENCES membre(id) ON DELETE CASCADE,
            type text NOT NULL DEFAULT 'question',
            sujet text NOT NULL,
            champ_concerne text,
            statut text NOT NULL DEFAULT 'ouverte',
            cree_le timestamptz DEFAULT now(),
            maj_le timestamptz DEFAULT now(),
            CONSTRAINT demande_type_chk CHECK (type IN ({type_chk})),
            CONSTRAINT demande_statut_chk CHECK (statut IN ({statut_chk}))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS demande_message (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            demande_id uuid NOT NULL REFERENCES demande(id) ON DELETE CASCADE,
            auteur_type text NOT NULL DEFAULT 'membre',
            auteur_nom text,
            corps text NOT NULL,
            cree_le timestamptz DEFAULT now(),
            CONSTRAINT demande_message_auteur_chk CHECK (auteur_type IN ('membre', 'staff'))
        )
        """
    )
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS champs_deverrouilles text[]")
    op.execute("CREATE INDEX IF NOT EXISTS idx_demande_membre ON demande(membre_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_demande_message_demande ON demande_message(demande_id)")

    for table in ("demande", "demande_message"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS {table}_self ON {table}")
        op.execute(
            f"CREATE POLICY {table}_self ON {table} FOR ALL "
            f"USING (adsum_current_role() = 'membre') WITH CHECK (adsum_current_role() = 'membre')"
        )
        op.execute(f"DROP POLICY IF EXISTS {table}_staff_read ON {table}")
        op.execute(
            f"CREATE POLICY {table}_staff_read ON {table} FOR SELECT "
            f"USING (adsum_current_role() = ANY({LECTURE}))"
        )
        op.execute(f"DROP POLICY IF EXISTS {table}_staff_write ON {table}")
        op.execute(
            f"CREATE POLICY {table}_staff_write ON {table} FOR ALL "
            f"USING (adsum_current_role() = ANY({STAFF})) WITH CHECK (adsum_current_role() = ANY({STAFF}))"
        )


def downgrade() -> None:
    for table in ("demande", "demande_message"):
        op.execute(f"DROP POLICY IF EXISTS {table}_self ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_staff_read ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_staff_write ON {table}")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS champs_deverrouilles")
    op.execute("DROP TABLE IF EXISTS demande_message CASCADE")
    op.execute("DROP TABLE IF EXISTS demande CASCADE")
