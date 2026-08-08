# ruff: noqa: E501 - migrations carry long SQL lines
"""Make the e-mail settings exist, so the back office can actually change them.

The gateway was built to switch providers from configuration, and it cannot. Three
things stood in the way, and all three are settings rather than code.

The rows were never created by a migration. They were typed straight into this one
database, so ``PUT /admin/integrations/{cle}`` answers ``404 unknown setting`` for
anything that was not typed. The interface lists ``email_smtp_password`` as an
editable field and saving it has always failed. Worse for a platform meant to be sold:
an organisation installing ADSUM tomorrow gets a base with no e-mail settings at all,
an interface that refuses to create them, and therefore no way to send anything.

One API key was shared by every HTTP provider. ``_api_key()`` fed both Brevo and
Resend, so a fallback chain of ``brevo,resend`` handed Brevo's key to Resend, which
rejected it. The chain failed at the exact moment it was supposed to rescue a send.
Each provider now has its own key, with the old single key kept as a fallback so
nothing breaks for the organisation running today.

An SMTP relay usually refuses to send as somebody else. A residential provider in
particular (Bouygues, Free) accepts only its own account address as the sender, so
sending "from" a Gmail address through it is rejected or silently rewritten.
``email_smtp_from`` lets the SMTP path carry its own sender without disturbing the
address used by the API providers.

Every insert is guarded by WHERE NOT EXISTS: an existing value is never overwritten,
and running this twice changes nothing.

Revision ID: 0195_reglages_email_fournisseur
Revises: 0194_participation_semantique
Create Date: 2026-08-08
"""
from __future__ import annotations

from alembic import op

revision = "0195_reglages_email_fournisseur"
down_revision = "0194_participation_semantique"
branch_labels = None
depends_on = None

#: Every setting the e-mail gateway reads, with the value a fresh installation starts
#: from. Empty means "not configured yet"; the interface will show the field and the
#: administrator can fill it. What matters is that the row EXISTS, because that is
#: what makes it editable.
_REGLAGES: tuple[tuple[str, str, str], ...] = (
    # (clé, valeur initiale, catégorie)
    ("email_provider", "console", "email"),
    ("email_from", "", "email"),
    ("email_from_name", "", "email"),
    # Where a member should write back. Left empty, replies land on the sending
    # mailbox, which on a no-reply address nobody reads.
    ("email_reply_to", "", "email"),
    # One key per HTTP provider, so a fallback chain can actually be armed.
    ("email_api_key_brevo", "", "email"),
    ("email_api_key_resend", "", "email"),
    # SMTP, usable with any mailbox provider: Infomaniak, o2switch, an ISP, a host.
    ("email_smtp_host", "", "email"),
    ("email_smtp_port", "587", "email"),
    ("email_smtp_user", "", "email"),
    ("email_smtp_password", "", "email"),
    # Most relays refuse to send as an address they do not own. Left empty, the SMTP
    # path uses the ordinary sender; filled, it overrides it for that path only.
    ("email_smtp_from", "", "email"),
)


def upgrade() -> None:
    for cle, valeur, categorie in _REGLAGES:
        op.execute(
            "INSERT INTO integration_config (cle, valeur, categorie) "
            f"SELECT '{cle}', {'NULL' if valeur == '' else repr(valeur)}, '{categorie}' "
            f"WHERE NOT EXISTS (SELECT 1 FROM integration_config WHERE cle = '{cle}')"
        )

    # The existing single key becomes the Brevo key when Brevo is the active provider
    # and no per-provider key has been set. Without this, arming the chain would
    # silently disarm the provider that works today.
    op.execute(
        "UPDATE integration_config SET valeur = ("
        "  SELECT valeur FROM integration_config WHERE cle = 'email_api_key'"
        ") "
        "WHERE cle = 'email_api_key_brevo' AND coalesce(valeur, '') = '' "
        "AND EXISTS (SELECT 1 FROM integration_config WHERE cle = 'email_api_key' AND coalesce(valeur, '') <> '') "
        "AND EXISTS (SELECT 1 FROM integration_config WHERE cle = 'email_provider' AND valeur LIKE '%brevo%')"
    )

    op.execute(
        "COMMENT ON TABLE integration_config IS "
        "'Réglages d''intégration modifiables par l''administration sans déploiement. "
        "Une clé absente de cette table ne peut pas être renseignée depuis le "
        "back-office : toute nouvelle clé doit donc être créée par une migration.'"
    )


def downgrade() -> None:
    # Only the rows this migration introduces, and only when still empty: a value an
    # administrator has since filled in is never destroyed by a rollback.
    for cle in (
        "email_reply_to", "email_api_key_brevo", "email_api_key_resend", "email_smtp_from",
    ):
        op.execute(
            f"DELETE FROM integration_config WHERE cle = '{cle}' AND coalesce(valeur, '') = ''"
        )
