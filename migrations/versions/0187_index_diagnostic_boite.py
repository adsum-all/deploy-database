# ruff: noqa: E501 - migrations carry long SQL lines
"""Make the mailbox diagnostic readable from an index, and stop the event log growing forever.

The login screen now tells a member when their mailbox has been refusing the code.
That answer comes from a lookup on email_delivery_event by recipient, and the lookup
is case-insensitive because an address is the same address whatever its casing.

The index created with the table, idx_email_event_destinataire on (destinataire,
survenu_le DESC), cannot serve a predicate on lower(destinataire): a btree over the
raw column says nothing about the lowered one, so PostgreSQL falls back to a
sequential scan. That is invisible on an empty table and becomes a slow login for
everyone once the log has grown, on the one code path where slowness is least
acceptable. This adds the matching expression index.

The second half is the growth itself. Nothing ever removed a delivery event, and the
diagnostic only ever reads the recent window, so the older rows cost storage and scan
time while answering no question. They are deleted after ninety days, which is longer
than any support conversation about a missing message and short enough to keep the
table small. Ninety days is also what the outbox retention already assumes.

Revision ID: 0187_index_diagnostic_boite
Revises: 0186_sommet_hierarchie
Create Date: 2026-08-02
"""
from __future__ import annotations

from alembic import op

revision = "0187_index_diagnostic_boite"
down_revision = "0186_sommet_hierarchie"
branch_labels = None
depends_on = None

# How long a delivery event stays useful. Past this, it answers no question anyone asks.
_RETENTION_JOURS = 90


def upgrade() -> None:
    # CONCURRENTLY needs its own transaction: it cannot run inside the one Alembic
    # opens. autocommit_block is how this repository already builds live indexes.
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_email_event_destinataire_lower "
            "ON email_delivery_event (lower(destinataire), survenu_le DESC) "
            "WHERE statut_normalise IN ('rebondi', 'rejete')"
        )
    op.execute(
        "COMMENT ON INDEX idx_email_event_destinataire_lower IS "
        "'Sert le diagnostic de boîte affiché à la connexion : recherche insensible à la casse "
        "sur les seuls événements de refus, les seuls que ce diagnostic lit.'"
    )

    # Retention. Written as a function so a scheduled job can call it, and run once
    # here so the table starts clean instead of waiting for the first scheduled run.
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION purger_email_delivery_event(jours integer DEFAULT {_RETENTION_JOURS})
        RETURNS integer
        LANGUAGE plpgsql
        AS $$
        DECLARE
            supprimes integer;
        BEGIN
            DELETE FROM email_delivery_event
            WHERE survenu_le < now() - make_interval(days => jours);
            GET DIAGNOSTICS supprimes = ROW_COUNT;
            RETURN supprimes;
        END;
        $$
        """
    )
    op.execute(
        "COMMENT ON FUNCTION purger_email_delivery_event(integer) IS "
        "'Supprime les événements de livraison plus anciens que la rétention. "
        "Retourne le nombre de lignes supprimées.'"
    )
    op.execute(f"SELECT purger_email_delivery_event({_RETENTION_JOURS})")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS purger_email_delivery_event(integer)")
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS idx_email_event_destinataire_lower")
