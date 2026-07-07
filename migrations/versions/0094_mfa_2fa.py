"""Two-factor authentication: member opt-in, channel preference, trusted devices.

Adds the member-controlled 2FA state to `utilisateur` (distinct from the existing
admin `double_facteur` flag, which is never read at login) and a `appareil_confiance`
table so a member can trust a device for 30 days and skip the code during that
window. Defaults keep 2FA opt-in (mfa_actif false), so no member is locked out on
rollout: existing sessions keep working and 2FA only engages once a member enables
it (or once the universal baseline is switched on in config).

Revision ID: 0094_mfa_2fa
Revises: 0093_membre_theme
"""
from __future__ import annotations

from alembic import op

revision = "0094_mfa_2fa"
down_revision = "0093_membre_theme"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Member-controlled 2FA state on the auth entity.
    op.execute("ALTER TABLE utilisateur ADD COLUMN IF NOT EXISTS mfa_actif boolean NOT NULL DEFAULT false")
    op.execute("ALTER TABLE utilisateur ADD COLUMN IF NOT EXISTS mfa_canal text NOT NULL DEFAULT 'auto'")
    op.execute(
        "ALTER TABLE utilisateur ADD CONSTRAINT utilisateur_mfa_canal_chk "
        "CHECK (mfa_canal IN ('auto', 'telegram', 'email'))"
    )
    # Nudge tracking: when 2FA was first recommended and when the member was last
    # nudged, so the 6-month reminder stays gentle and spaced.
    op.execute("ALTER TABLE utilisateur ADD COLUMN IF NOT EXISTS mfa_recommande_le timestamptz")
    op.execute("ALTER TABLE utilisateur ADD COLUMN IF NOT EXISTS mfa_derniere_relance timestamptz")

    # Trusted devices: a login from one of these skips the code until expire_le.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS appareil_confiance (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            utilisateur_id uuid NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE,
            device_hash text NOT NULL,
            libelle text,
            cree_le timestamptz NOT NULL DEFAULT now(),
            derniere_verif_le timestamptz NOT NULL DEFAULT now(),
            expire_le timestamptz NOT NULL,
            revoque boolean NOT NULL DEFAULT false,
            CONSTRAINT appareil_confiance_uq UNIQUE (utilisateur_id, device_hash)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_appareil_confiance_actif "
        "ON appareil_confiance (utilisateur_id) WHERE revoque = false"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS appareil_confiance")
    op.execute("ALTER TABLE utilisateur DROP COLUMN IF EXISTS mfa_derniere_relance")
    op.execute("ALTER TABLE utilisateur DROP COLUMN IF EXISTS mfa_recommande_le")
    op.execute("ALTER TABLE utilisateur DROP CONSTRAINT IF EXISTS utilisateur_mfa_canal_chk")
    op.execute("ALTER TABLE utilisateur DROP COLUMN IF EXISTS mfa_canal")
    op.execute("ALTER TABLE utilisateur DROP COLUMN IF EXISTS mfa_actif")
