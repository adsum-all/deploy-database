"""Data retention: keep member data for a renewable window with yearly consent.

The business keeps each member's profile photo and provided data for a renewable
period (default two years) rather than deleting anything at validation. A yearly
notice reminds the member their data is kept and renews the retention window
unless they object (auto-acceptance), satisfying the RGPD storage-limitation and
information duties without losing the record.

Adds the retention columns, the retention-window setting, and the renewal
notification type and templates (French of France with correct diacritics).

Revision ID: 0039_retention_conservation
Revises: 0038_signatures_par_type
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0039_retention_conservation"
down_revision = "0038_signatures_par_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS retention_echeance timestamptz")
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS retention_consentement_le timestamptz")
    op.execute(
        "INSERT INTO integration_config (cle, valeur, categorie) VALUES ('retention_annees', '2', 'retention') "
        "ON CONFLICT (cle) DO NOTHING"
    )
    op.execute(
        "INSERT INTO type_notification (cle, libelle, categorie, actif, scheduled) "
        "VALUES ('retention_renouvellement', 'Renouvellement de conservation', 'inscription', true, true) "
        "ON CONFLICT (cle) DO NOTHING"
    )
    op.execute(
        "INSERT INTO modele_message (cle, titre, corps, titre_en, corps_en, categorie) VALUES "
        "('retention_renouvellement', "
        "'Conservation de vos données : renouvellement', "
        "'Bonjour {prenom}, conformément à notre politique de confidentialité, vos données et votre photo sont "
        "conservées de manière sécurisée pour une nouvelle période de {annees} ans. Aucune action n''est requise : "
        "cette conservation est renouvelée automatiquement. Si vous souhaitez exercer vos droits (accès, rectification, "
        "effacement), contactez l''administration à tout moment.', "
        "'Retention of your data: renewal', "
        "'Hello {prenom}, in accordance with our privacy policy, your data and your photo are securely kept for a new "
        "period of {annees} years. No action is required: this retention renews automatically. To exercise your rights "
        "(access, rectification, erasure), contact the administration at any time.', "
        "'inscription') ON CONFLICT (cle) DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DELETE FROM modele_message WHERE cle = 'retention_renouvellement'")
    op.execute("DELETE FROM type_notification WHERE cle = 'retention_renouvellement'")
    op.execute("DELETE FROM integration_config WHERE cle = 'retention_annees'")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS retention_consentement_le")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS retention_echeance")
