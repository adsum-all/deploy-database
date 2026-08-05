# ruff: noqa: E501 - migrations carry long SQL lines
"""Say which permission can be exercised from which application, and mean it.

An access group carries an application tag. Nothing ever said what a right means for
a given application, so the tag bounded nothing: a right granted inside the
collaboration workspace applied to the back office as well.

This table is the missing referential. Once it exists, a membership tagged for one
application contributes only the permissions declared for that application, and the
tag finally does what its name says.

The seed is derived from the permission domain, read from the permission table so the
migration stays self-contained and works against whatever the base actually holds. It
is a starting point, not a verdict: deciding that reading the statistics belongs to
Pilotage rather than to Direction is an organisational choice, and the permissions
screen lets it be changed.

The back office holds every permission on purpose. It is the administration console;
bounding it would leave an administrator unable to administer from the one place built
for it. Self-scoped permissions are excluded: what a member does for themselves never
comes from a group, so pairing them with an application would suggest an
administration that cannot happen.

Revision ID: 0180_permission_par_application
Revises: 0179_acces_applicatif_explicite
Create Date: 2026-07-28
"""
from __future__ import annotations

from alembic import op

revision = "0180_permission_par_application"
down_revision = "0179_acces_applicatif_explicite"
branch_labels = None
depends_on = None


def _lit(v: str) -> str:
    """A SQL string literal, quotes doubled. Same helper as 0175."""
    return "'" + v.replace("'", "''") + "'"

# Domain to the applications it can be exercised from, beyond the back office.
# Kept here in full so the migration does not depend on application code.
_DOMAINES = {
    "collaboration": ("collaboration",),
    "canal": ("collaboration",),
    "modeles": ("collaboration",),
    "controle": ("controleur",),
    "comptage": ("controleur",),
    "terminaux": ("controleur",),
    "statistiques": ("pilotage", "direction"),
    "participation": ("pilotage", "direction"),
    "evenements": ("pilotage", "direction"),
    "tags": ("pilotage",),
    "organisation": ("pilotage", "direction"),
    "commissions": ("pilotage", "direction"),
    "tribus": ("pilotage", "direction"),
    "bergers": ("pilotage", "direction"),
    "membres": ("pilotage", "direction"),
    "anniversaires": ("pilotage",),
    "communication": ("direction",),
    "notifications": ("direction",),
}


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS permission_application (
            permission        text NOT NULL REFERENCES permission(cle) ON DELETE CASCADE,
            application_code  text NOT NULL REFERENCES application(code) ON DELETE CASCADE,
            cree_le           timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (permission, application_code)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS permission_application_app_idx "
        "ON permission_application (application_code)"
    )
    # Read-only for the public roles: the referential decides what a right means, so
    # it is administered through the API and never written from a client connection.
    op.execute("ALTER TABLE permission_application ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON permission_application FROM anon, authenticated")

    # The administration console exercises every permission that a group can grant.
    op.execute(
        """
        INSERT INTO permission_application (permission, application_code)
        SELECT p.cle, 'back-office'
          FROM permission p
         WHERE COALESCE(p.portee, '') <> 'self'
           AND EXISTS (SELECT 1 FROM application a WHERE a.code = 'back-office')
        ON CONFLICT DO NOTHING
        """
    )

    # Then one pair per domain declared above, skipping any application the base does
    # not know: seeding a code that does not exist would fail the foreign key and
    # roll back a migration over a naming difference.
    couples: list[tuple[str, str]] = []
    for domaine, applications in _DOMAINES.items():
        for application in applications:
            couples.append((domaine, application))
    if not couples:
        return
    # One multi-row statement rather than a loop: the pooled connection reuses
    # prepared statement names, and a loop collides on them.
    #
    # Written with the values inlined rather than bound, so the migration also
    # renders under `alembic upgrade --sql`. Driver-level parameter binding needs a
    # live connection, and offline mode supplies a stand-in that has none, which made
    # the whole chain unrenderable and the schema test unable to run. The values are
    # the module constants above, never anything from outside, and _lit doubles quotes.
    valeurs = ", ".join(f"({_lit(d)}, {_lit(a)})" for d, a in couples)
    op.execute(
        "INSERT INTO permission_application (permission, application_code) "
        "SELECT p.cle, v.a "
        f"FROM (VALUES {valeurs}) AS v(d, a) "
        "JOIN permission p ON p.domaine = v.d AND COALESCE(p.portee, '') <> 'self' "
        "WHERE EXISTS (SELECT 1 FROM application ap WHERE ap.code = v.a) "
        "ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS permission_application")
