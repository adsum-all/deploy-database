"""Country e-signature matrix and manual-attestation follow-up.

An admin-editable matrix classifies countries for electronic-signature
acceptance and whether a hand-signed attestation is required in addition (for
example Cote d'Ivoire, where the handwritten-equivalent value requires a secure
signature). When a member from such a country is approved, a one-month manual
attestation task opens, with reminders and automatic invalidation on expiry.

Revision ID: 0034_pays_attestation
Revises: 0033_esignature
Create Date: 2026-07-01
"""
# ruff: noqa: E501
from __future__ import annotations

from alembic import op

revision = "0034_pays_attestation"
down_revision = "0033_esignature"
branch_labels = None
depends_on = None

# Country classification (v1, editable by the admin). manuel_requis = a hand
# signed attestation is required in addition to the electronic signature.
_PAYS = [
    ("CI", "Cote d'Ivoire", "Ivory Coast", True, True, "Loi 2013-546 sur les transactions electroniques ; equivalence manuscrite = signature securisee (PSCE agree ARTCI)"),
    ("FR", "France", "France", True, False, "Reglement eIDAS (UE) 910/2014 ; Code civil art. 1366-1367"),
    ("BE", "Belgique", "Belgium", True, False, "Reglement eIDAS 910/2014"),
    ("CH", "Suisse", "Switzerland", True, False, "Loi federale sur la signature electronique (SCSE)"),
    ("CA", "Canada", "Canada", True, False, "PIPEDA + lois provinciales (UECA)"),
    ("US", "United States", "United States", True, False, "ESIGN Act (2000) + UETA"),
    ("GB", "Royaume-Uni", "United Kingdom", True, False, "Electronic Communications Act 2000 / UK eIDAS"),
    ("SN", "Senegal", "Senegal", True, True, "Loi 2008-08 ; renfort manuel par prudence"),
    ("CM", "Cameroun", "Cameroon", True, True, "Cadre en construction ; renfort manuel par prudence"),
    ("GH", "Ghana", "Ghana", True, True, "Electronic Transactions Act 2008 ; renfort manuel par prudence"),
    ("NG", "Nigeria", "Nigeria", True, True, "Evidence Act 2011 ; renfort manuel par prudence"),
]


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pays_signature (
            code_pays text PRIMARY KEY,
            nom text NOT NULL,
            nom_en text,
            esignature_reconnue boolean NOT NULL DEFAULT true,
            manuel_requis boolean NOT NULL DEFAULT false,
            source text,
            note text,
            maj_par uuid,
            maj_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    for code, nom, nom_en, reconnue, manuel, source in _PAYS:
        op.execute(
            "INSERT INTO pays_signature (code_pays, nom, nom_en, esignature_reconnue, manuel_requis, source) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (code_pays) DO NOTHING",
            (code, nom, nom_en, reconnue, manuel, source),
        )
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS attestation_statut text NOT NULL DEFAULT 'not_required'")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS attestation_manuelle (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            membre_id uuid NOT NULL REFERENCES membre(id) ON DELETE CASCADE,
            signature_id uuid,
            statut text NOT NULL DEFAULT 'awaiting',
            document_id uuid,
            echeance timestamptz,
            ouverte_le timestamptz NOT NULL DEFAULT now(),
            valide_le timestamptz,
            valide_par uuid
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_attestation_statut ON attestation_manuelle (statut, echeance)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS attestation_manuelle")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS attestation_statut")
    op.execute("DROP TABLE IF EXISTS pays_signature")
