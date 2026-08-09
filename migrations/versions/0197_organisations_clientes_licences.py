# ruff: noqa: E501 - migrations carry long SQL lines
"""Client organisations and their licences, seen from the publisher's side.

The platform is built to be sold, and nothing in the schema knows that. There is one
organisation, implicitly, and no notion at all of a customer: no contract, no plan, no
expiry, no way to suspend an unpaid account or grant a free one. The commercial reality
lives in somebody's memory and in an invoice folder.

Two tables.

``organisation_cliente`` is the customer. It carries who they are, how to reach them,
and the state of their access. ``etat`` is deliberately not a boolean: an organisation
being evaluated, one running normally, one suspended for non-payment and one that has
left are four different situations, and collapsing them loses the only information that
tells you what to do next.

``licence`` is what they are entitled to and until when. A licence is never edited in
place: granting a new one supersedes the previous, which stays for the history. An
organisation that argues about what it was promised is settled by reading the row, not
by remembering the conversation.

Suspension carries a reason and an author, always. A client asking why they are locked
out deserves an answer better than "the system did it", and whoever suspended them must
be identifiable.

What this migration deliberately does NOT do: attach existing data to an organisation.
Retrofitting a tenant column onto a hundred and forty tables is a separate, dangerous
piece of work that must be done with the current organisation already recorded and
verified. This lays the commercial layer; the isolation layer comes after, on purpose.

Revision ID: 0197_org_clientes_licences
Revises: 0196_support_fils_messages
Create Date: 2026-08-09
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0197_org_clientes_licences"
down_revision = "0196_support_fils_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS organisation_cliente (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            code text NOT NULL UNIQUE,
            nom text NOT NULL,
            pays text,
            ville text,
            contact_nom text,
            contact_email text,
            contact_telephone text,
            etat text NOT NULL DEFAULT 'evaluation',
            suspendue_motif text,
            suspendue_par uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            suspendue_le timestamptz,
            note text,
            cree_le timestamptz NOT NULL DEFAULT now(),
            maj_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("ALTER TABLE organisation_cliente DROP CONSTRAINT IF EXISTS organisation_cliente_etat_check")
    op.execute(
        "ALTER TABLE organisation_cliente ADD CONSTRAINT organisation_cliente_etat_check "
        "CHECK (etat IN ('evaluation', 'active', 'suspendue', 'resiliee'))"
    )
    # A suspension with no reason and no author is the kind of state nobody can undo
    # with confidence, because nobody knows why it was set.
    op.execute("ALTER TABLE organisation_cliente DROP CONSTRAINT IF EXISTS organisation_cliente_suspension_tracee")
    op.execute(
        "ALTER TABLE organisation_cliente ADD CONSTRAINT organisation_cliente_suspension_tracee "
        "CHECK ((etat = 'suspendue') = (suspendue_motif IS NOT NULL AND suspendue_le IS NOT NULL))"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS licence (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            organisation_id uuid NOT NULL REFERENCES organisation_cliente(id) ON DELETE CASCADE,
            formule text NOT NULL,
            membres_inclus integer,
            debut date NOT NULL,
            fin date,
            gracieuse boolean NOT NULL DEFAULT false,
            motif text,
            accordee_par uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            remplacee_le timestamptz,
            cree_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("ALTER TABLE licence DROP CONSTRAINT IF EXISTS licence_periode_coherente")
    # A licence that ends before it starts is a data-entry slip that would silently
    # make an organisation unlicensed from day one.
    op.execute(
        "ALTER TABLE licence ADD CONSTRAINT licence_periode_coherente CHECK (fin IS NULL OR fin >= debut)"
    )
    op.execute("ALTER TABLE licence DROP CONSTRAINT IF EXISTS licence_membres_positifs")
    op.execute(
        "ALTER TABLE licence ADD CONSTRAINT licence_membres_positifs "
        "CHECK (membres_inclus IS NULL OR membres_inclus > 0)"
    )
    # Only one licence in force per organisation at a time. Two overlapping licences
    # make "what are they entitled to" unanswerable, which is the single question this
    # table exists to answer.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS licence_en_vigueur_uniq "
        "ON licence (organisation_id) WHERE remplacee_le IS NULL"
    )
    op.execute("CREATE INDEX IF NOT EXISTS licence_organisation_idx ON licence (organisation_id, cree_le DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS organisation_cliente_etat_idx ON organisation_cliente (etat, nom)")

    # The organisation running today is recorded from the brand it already publishes,
    # rather than invented: the console must show the real customer from the first
    # screen, not an empty list next to a live platform.
    op.execute(
        sa.text(
            "INSERT INTO organisation_cliente (code, nom, etat, note) "
            "SELECT 'sacerdoce-royal', "
            "  coalesce(nullif((SELECT valeur FROM integration_config WHERE cle = 'org_marque'), ''), 'Sacerdoce Royal'), "
            "  'active', :note "
            "WHERE NOT EXISTS (SELECT 1 FROM organisation_cliente WHERE code = 'sacerdoce-royal')"
        ).bindparams(
            note="Organisation historique, en production. Enregistrée par la migration 0197 à partir de la marque configurée."
        )
    )

    for table in ("organisation_cliente", "licence"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON {table} FROM anon")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS licence")
    op.execute("DROP TABLE IF EXISTS organisation_cliente")
