# ruff: noqa: E501 - migrations carry long SQL lines
"""Which host serves which organisation, and where that organisation's data lives.

The isolation model the owner ruled on is one database per organisation, with no path
by which one client's data can reach another: not at the infrastructure, not in the
database, not in the backend, not in the frontend. The alternative, a shared base with a
tenant column, makes isolation depend on eighteen hundred hand-written queries all
filtering correctly, forever. One omission is a data breach.

For that to work the platform must know, before running any query, which database this
request belongs to. It knows it from the host the request arrived on, and this table is
where that mapping lives.

The connection string is stored here rather than in an environment variable because the
set of organisations changes at the pace of sales, not at the pace of deployments: a new
client must not require a redeployment to become reachable.

On the secret. A connection string carries a password, so this table is readable only
through the API's own role, like every other table, and the console never returns it.
Storing it is not a new exposure: whoever can read this table can already read every
other one, and an environment variable would put the same secret in a place that changes
only by redeploying.

While the table is empty the platform stays on its historical connection, which is how
production keeps running. The moment one row exists, an unmatched host is refused rather
than served from a default: a misconfigured domain must never quietly hand one
organisation's data out under another organisation's address.

Revision ID: 0198_organisation_hote
Revises: 0197_org_clientes_licences
Create Date: 2026-08-09
"""
from __future__ import annotations

from alembic import op

revision = "0198_organisation_hote"
down_revision = "0197_org_clientes_licences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS organisation_hote (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            organisation_id uuid NOT NULL REFERENCES organisation_cliente(id) ON DELETE CASCADE,
            hote text NOT NULL,
            dsn text,
            note text,
            cree_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    # One host serves exactly one organisation. Two rows for the same host would make
    # the resolution depend on row order, which is the one thing it must never do.
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS organisation_hote_uniq ON organisation_hote (lower(hote))")
    op.execute("CREATE INDEX IF NOT EXISTS organisation_hote_org_idx ON organisation_hote (organisation_id)")
    # Stored lower-case and without a port, so a lookup never has to guess a spelling.
    op.execute("ALTER TABLE organisation_hote DROP CONSTRAINT IF EXISTS organisation_hote_forme")
    op.execute(
        "ALTER TABLE organisation_hote ADD CONSTRAINT organisation_hote_forme "
        "CHECK (hote = lower(hote) AND hote !~ ':' AND hote !~ '/' AND length(hote) BETWEEN 3 AND 253)"
    )
    op.execute("ALTER TABLE organisation_hote ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON organisation_hote FROM anon")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS organisation_hote")
