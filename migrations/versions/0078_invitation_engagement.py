# ruff: noqa: E501 - migrations carry long SQL lines
"""Public engagement intake: people who express interest via a public-event QR code.

A distinct pre-registration structure, clearly separate from real member accounts.
A person scans the engagement QR (or is entered manually / imported from Excel) and
lands here as a lead, not yet a member. An internal team later converts selected
leads into real member registrations. E-mail is unique so nobody is captured twice.

Revision ID: 0078_invitation_engagement
Revises: 0077_guard_super_admin
Create Date: 2026-07-06
"""
from __future__ import annotations

from alembic import op

revision = "0078_invitation_engagement"
down_revision = "0077_guard_super_admin"
branch_labels = None
depends_on = None

_SELECT = ["super_admin", "admin", "gestionnaire", "direction", "controleur"]
_WRITE = ["super_admin", "admin", "gestionnaire"]


def _array(roles):
    return "ARRAY[" + ", ".join(f"'{r}'" for r in roles) + "]::text[]"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS invitation_engagement (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            email text NOT NULL,
            prenoms text,
            nom text,
            telephone text,
            pays_indicatif text,
            pays_code text,
            source text NOT NULL DEFAULT 'qr',
            evenement_id uuid REFERENCES evenement(id) ON DELETE SET NULL,
            statut text NOT NULL DEFAULT 'en_attente',
            membre_id uuid REFERENCES membre(id) ON DELETE SET NULL,
            remerciement_envoye boolean NOT NULL DEFAULT false,
            remerciement_canal text,
            cree_par uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            cree_le timestamptz NOT NULL DEFAULT now(),
            converti_le timestamptz,
            CONSTRAINT invitation_engagement_source_chk CHECK (source IN ('qr', 'manuel', 'import')),
            CONSTRAINT invitation_engagement_statut_chk CHECK (statut IN ('en_attente', 'converti'))
        )
        """
    )
    # Global e-mail uniqueness (case-insensitive): a person is captured once, whatever
    # the collection channel (QR / manual / Excel).
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS invitation_engagement_email_uq ON invitation_engagement (lower(email))")
    op.execute("CREATE INDEX IF NOT EXISTS invitation_engagement_statut_idx ON invitation_engagement (statut)")
    op.execute("CREATE INDEX IF NOT EXISTS invitation_engagement_evenement_idx ON invitation_engagement (evenement_id)")
    op.execute("ALTER TABLE invitation_engagement ENABLE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY invitation_engagement_select ON invitation_engagement FOR SELECT USING (adsum_current_role() = ANY({_array(_SELECT)}))")
    op.execute(f"CREATE POLICY invitation_engagement_write ON invitation_engagement FOR ALL USING (adsum_current_role() = ANY({_array(_WRITE)})) WITH CHECK (adsum_current_role() = ANY({_array(_WRITE)}))")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS invitation_engagement_write ON invitation_engagement")
    op.execute("DROP POLICY IF EXISTS invitation_engagement_select ON invitation_engagement")
    op.execute("DROP TABLE IF EXISTS invitation_engagement CASCADE")
