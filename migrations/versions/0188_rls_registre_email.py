# ruff: noqa: E501 - migrations carry long SQL lines
"""Put row level security on the two e-mail ledger tables, the last ones without it.

The Constitution requires row level security on every table. email_outbox and
email_delivery_event shipped without any, and they were the only two left: a count
over the rendered schema gives 144 tables and 142 statements enabling the feature.
They are also among the tables that most deserve it, since they hold recipient
addresses in clear together with whatever the provider returned about them.

Reading is for the roles that administer communications. The exception is the
mailbox diagnostic shown at sign-in: it must read the events of the address whose
password was just validated, under that member's own role. A policy cannot know
which address that is, so the application puts it in the transaction as
adsum.diagnostic_email and the policy matches on it. The value is server-side and
canonical, so a member can see the events of their own address and of no other, and
an ordinary role that sets nothing sees nothing.

Writing stays with the administrative roles. The application writes to the ledger on
the schema owner's connection, which is not subject to these policies, so recording a
send keeps working on every path, including the ones that run before anyone is
authenticated. That is deliberate: an observability layer that can be silenced by an
authorization rule stops being observability.

Revision ID: 0188_rls_registre_email
Revises: 0187_index_diagnostic_boite
Create Date: 2026-08-02
"""
from __future__ import annotations

from alembic import op

revision = "0188_rls_registre_email"
down_revision = "0187_index_diagnostic_boite"
branch_labels = None
depends_on = None

# Who administers communications, and may therefore read the ledger in full.
_LECTURE = "ARRAY['super_admin', 'admin', 'gestionnaire', 'direction']::text[]"
_ECRITURE = "ARRAY['super_admin', 'admin', 'gestionnaire']::text[]"

# The address the current transaction is allowed to look up, empty when none was set.
_ADRESSE_DEMANDEE = "lower(NULLIF(current_setting('adsum.diagnostic_email', true), ''))"

_TABLES = ("email_outbox", "email_delivery_event")


def upgrade() -> None:
    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

        op.execute(f"DROP POLICY IF EXISTS {table}_lecture ON {table}")
        op.execute(
            f"CREATE POLICY {table}_lecture ON {table} FOR SELECT USING ("
            f"  adsum_current_role() = ANY({_LECTURE})"
            f"  OR lower(destinataire) = {_ADRESSE_DEMANDEE}"
            f")"
        )

        op.execute(f"DROP POLICY IF EXISTS {table}_ecriture ON {table}")
        op.execute(
            f"CREATE POLICY {table}_ecriture ON {table} FOR ALL "
            f"USING (adsum_current_role() = ANY({_ECRITURE})) "
            f"WITH CHECK (adsum_current_role() = ANY({_ECRITURE}))"
        )

    op.execute(
        "COMMENT ON POLICY email_delivery_event_lecture ON email_delivery_event IS "
        "'Lecture complète pour les rôles qui administrent les communications. "
        "Un autre rôle ne voit que les événements de l''adresse posée par le serveur "
        "dans adsum.diagnostic_email, c''est-à-dire la sienne au moment de sa connexion.'"
    )


def downgrade() -> None:
    for table in _TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_lecture ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_ecriture ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
