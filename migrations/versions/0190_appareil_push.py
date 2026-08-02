# ruff: noqa: E501 - migrations carry long SQL lines
"""Hold the devices a member wants notified, so the mobile application can be reached.

The platform reaches its members by e-mail, Telegram, WhatsApp and SMS. The Android
application it ships cannot be reached at all: nothing records where to send. A
member who installed it still learns about an activity by e-mail, which is the one
channel this base has watched fail.

A registration is (member, device token). The token is issued by the push service and
rotates on its own, so the same phone appears under a new token and the old one stops
working. Both facts shape this table: the token is unique, and a registration carries
its last successful use so a token the service has rejected can be retired instead of
being retried on every send forever.

The token is not a secret the member types, but it does address their phone, so the
table is readable only by the roles that administer communications, and a member
reaches their own registrations through the application rather than through the
table. Deleting the member deletes the registration: nothing here outlives the
account it describes.

The channel preference is added alongside. Without it a member who turns every push
channel off in the interface would still receive notifications on their phone,
because a channel nobody declared cannot be refused.

Revision ID: 0190_appareil_push
Revises: 0189_rls_type_evenement
Create Date: 2026-08-02
"""
from __future__ import annotations

from alembic import op

revision = "0190_appareil_push"
down_revision = "0189_rls_type_evenement"
branch_labels = None
depends_on = None

_LECTURE = "ARRAY['super_admin', 'admin', 'gestionnaire']::text[]"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS appareil_push (
            id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            membre_id     uuid NOT NULL REFERENCES membre(id) ON DELETE CASCADE,
            jeton         text NOT NULL,
            plateforme    text NOT NULL DEFAULT 'android',
            libelle       text,
            actif         boolean NOT NULL DEFAULT true,
            motif_retrait text,
            cree_le       timestamptz NOT NULL DEFAULT now(),
            vu_le         timestamptz NOT NULL DEFAULT now(),
            envoye_le     timestamptz,
            CONSTRAINT appareil_push_plateforme_connue CHECK (plateforme IN ('android', 'ios', 'web'))
        )
        """
    )
    # One token addresses one device. The service reissues it to the same phone after
    # a reinstall, and it must then belong to whoever signed in there, not to whoever
    # signed in there first: the registration endpoint reassigns on conflict.
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS appareil_push_jeton_uniq ON appareil_push (jeton)")
    # The send path asks for one member's live devices and nothing else.
    op.execute(
        "CREATE INDEX IF NOT EXISTS appareil_push_membre_actif "
        "ON appareil_push (membre_id) WHERE actif"
    )

    op.execute(
        "COMMENT ON COLUMN appareil_push.motif_retrait IS "
        "'Pourquoi le service d''envoi a refusé ce jeton. Renseigné au moment où "
        "l''appareil est désactivé, pour qu''un retrait se distingue d''une "
        "désinscription volontaire.'"
    )

    # Role-based, like membre and notification next door. Restricting a member to
    # their own rows belongs to the application, which knows who is asking; a policy
    # here would need a per-member setting this schema has never carried, and
    # inventing one for a single table would leave two conventions for the same rule.
    op.execute("ALTER TABLE appareil_push ENABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS appareil_push_lecture ON appareil_push")
    op.execute(
        f"CREATE POLICY appareil_push_lecture ON appareil_push FOR SELECT "
        f"USING (COALESCE(adsum_current_role(), '') = ANY({_LECTURE}))"
    )
    op.execute("DROP POLICY IF EXISTS appareil_push_ecriture ON appareil_push")
    op.execute(
        f"CREATE POLICY appareil_push_ecriture ON appareil_push FOR ALL "
        f"USING (COALESCE(adsum_current_role(), '') = ANY({_LECTURE})) "
        f"WITH CHECK (COALESCE(adsum_current_role(), '') = ANY({_LECTURE}))"
    )

    # The member's switch for this channel. Defaults to on, like the others: somebody
    # who installed the application asked to be reached on it.
    op.execute(
        "ALTER TABLE preference_notification "
        "ADD COLUMN IF NOT EXISTS push boolean NOT NULL DEFAULT true"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE preference_notification DROP COLUMN IF EXISTS push")
    op.execute("DROP POLICY IF EXISTS appareil_push_lecture ON appareil_push")
    op.execute("DROP POLICY IF EXISTS appareil_push_ecriture ON appareil_push")
    op.execute("DROP TABLE IF EXISTS appareil_push")
