# ruff: noqa: E501 - migrations carry long SQL lines
"""What an organisation has actually subscribed to, module by module.

The product is sold by module: one client takes the back office and the direction, another
takes everything, and the price follows the count. The catalogue of applications already
exists as data. What was missing is the link between a licence and the modules it covers,
so nothing could tell a subscribed module from an available one.

The owner's rule is explicit and shapes this table: **a module that has not been
subscribed is not deployed, and its API refuses access.** Hiding a button is decoration,
not a limit: the endpoints stay reachable to anyone who types the address, and the
platform would be selling on the honour system.

An empty set of modules means the whole catalogue, deliberately. The single organisation
running today subscribed to nothing in this table because the table did not exist, and
reading that as "no module" would take the platform offline the moment this migration
lands. Once a licence names one module, it names them all: the absence of a row is then
a refusal, not a silence.

Revision ID: 0199_licence_modules
Revises: 0198_organisation_hote
Create Date: 2026-08-09
"""
from __future__ import annotations

from alembic import op

revision = "0199_licence_modules"
down_revision = "0198_organisation_hote"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS licence_module (
            licence_id uuid NOT NULL REFERENCES licence(id) ON DELETE CASCADE,
            application_code text NOT NULL REFERENCES application(code) ON DELETE RESTRICT,
            cree_le timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (licence_id, application_code)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS licence_module_app_idx ON licence_module (application_code)")
    # The foreign key to application is RESTRICT rather than CASCADE on purpose: removing
    # an application from the catalogue while a client pays for it must fail loudly, not
    # silently cancel their subscription.
    op.execute("ALTER TABLE licence_module ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON licence_module FROM anon")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS licence_module")
