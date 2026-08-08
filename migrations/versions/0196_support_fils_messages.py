# ruff: noqa: E501 - migrations carry long SQL lines
"""Support conversations, so a member can reach a human and be answered.

Today a member who hits a technical problem has nowhere to go. There is no ticket,
no incident, no thread: the only inbound path in the whole platform is the webhook
that records what a provider reports after a message has already left. A request for
help either reaches a personal mailbox or it reaches nobody, and either way it leaves
no trace anyone can follow.

Two tables, deliberately few.

``support_fil`` is one conversation. It carries a human reference so it can be quoted
in a message or over the phone, a state, an assignee, and the origin of the request.
A thread opened from inside the application knows which account asked. A thread opened
by e-mail knows only an address, which is why ``demandeur_utilisateur_id`` is nullable
and ``demandeur_email`` is not: an unidentified sender must still be answerable.

``support_message`` is one exchange in that conversation, inbound or outbound. It keeps
the provider's ``message_id`` so a reply arriving by e-mail attaches to the thread it
answers instead of opening a new one, which is how a support mailbox turns into a pile
of disconnected fragments.

On personal data. Support exists to fix the platform, not to read member files. The
thread carries what is needed to answer a person (their name, their address, what they
wrote) and nothing else: no link to the member record, no health, no document, no
attendance. Whoever needs a member's file opens the back office, where that access is
already governed and audited.

Retention. A closed thread is not kept forever; ``ferme_le`` is indexed so a purge can
find what has aged out. The purge itself is a separate decision and is not created
here, because a retention rule nobody chose is a rule nobody honours.

Revision ID: 0196_support_fils_messages
Revises: 0195_reglages_email_fournisseur
Create Date: 2026-08-09
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0196_support_fils_messages"
down_revision = "0195_reglages_email_fournisseur"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS support_fil (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            reference text NOT NULL UNIQUE,
            sujet text NOT NULL,
            statut text NOT NULL DEFAULT 'nouveau',
            priorite text NOT NULL DEFAULT 'normale',
            categorie text NOT NULL DEFAULT 'autre',
            canal text NOT NULL DEFAULT 'application',
            application text,
            demandeur_utilisateur_id uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            demandeur_email text NOT NULL,
            demandeur_nom text,
            assigne_a uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            cree_le timestamptz NOT NULL DEFAULT now(),
            maj_le timestamptz NOT NULL DEFAULT now(),
            derniere_reponse_le timestamptz,
            ferme_le timestamptz
        )
        """
    )
    op.execute(
        "ALTER TABLE support_fil DROP CONSTRAINT IF EXISTS support_fil_statut_check"
    )
    op.execute(
        "ALTER TABLE support_fil ADD CONSTRAINT support_fil_statut_check "
        "CHECK (statut IN ('nouveau', 'en_cours', 'en_attente', 'resolu', 'clos'))"
    )
    op.execute(
        "ALTER TABLE support_fil DROP CONSTRAINT IF EXISTS support_fil_priorite_check"
    )
    op.execute(
        "ALTER TABLE support_fil ADD CONSTRAINT support_fil_priorite_check "
        "CHECK (priorite IN ('basse', 'normale', 'haute', 'critique'))"
    )
    op.execute(
        "ALTER TABLE support_fil DROP CONSTRAINT IF EXISTS support_fil_canal_check"
    )
    op.execute(
        "ALTER TABLE support_fil ADD CONSTRAINT support_fil_canal_check "
        "CHECK (canal IN ('application', 'email'))"
    )
    # A closed thread must say when it closed, and an open one must not pretend to.
    # Without this, retention has nothing reliable to work from.
    op.execute(
        "ALTER TABLE support_fil DROP CONSTRAINT IF EXISTS support_fil_fermeture_coherente"
    )
    op.execute(
        "ALTER TABLE support_fil ADD CONSTRAINT support_fil_fermeture_coherente "
        "CHECK ((statut IN ('resolu', 'clos')) = (ferme_le IS NOT NULL))"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS support_message (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            fil_id uuid NOT NULL REFERENCES support_fil(id) ON DELETE CASCADE,
            entrant boolean NOT NULL,
            auteur_utilisateur_id uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            auteur_nom text,
            auteur_email text,
            corps text NOT NULL,
            message_id text,
            envoye boolean NOT NULL DEFAULT false,
            erreur_envoi text,
            cree_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    # A provider re-delivering the same message must not duplicate the exchange. The
    # index is partial because a message created in the application has no Message-ID.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS support_message_message_id_uniq "
        "ON support_message (message_id) WHERE message_id IS NOT NULL"
    )
    op.execute("CREATE INDEX IF NOT EXISTS support_message_fil_idx ON support_message (fil_id, cree_le)")
    op.execute("CREATE INDEX IF NOT EXISTS support_fil_statut_idx ON support_fil (statut, maj_le DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS support_fil_demandeur_idx ON support_fil (demandeur_utilisateur_id, cree_le DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS support_fil_ferme_idx ON support_fil (ferme_le) WHERE ferme_le IS NOT NULL")

    # A reference a human can read out loud, unique per year, allocated by the database
    # so two simultaneous requests cannot receive the same one.
    op.execute("CREATE SEQUENCE IF NOT EXISTS support_reference_seq")

    # The categories a requester picks from. Administrable like the absence reasons,
    # because what an organisation gets asked about is not knowable in advance.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS support_categorie (
            code text PRIMARY KEY,
            libelle text NOT NULL,
            libelle_en text,
            ordre integer NOT NULL DEFAULT 50,
            actif boolean NOT NULL DEFAULT true,
            cree_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    for code, libelle, libelle_en, ordre in (
        ("connexion", "Problème de connexion", "Sign-in problem", 10),
        ("pointage", "Pointage ou présence", "Attendance or check-in", 20),
        ("compte", "Mon compte et mes informations", "My account and details", 30),
        ("technique", "Anomalie technique", "Technical fault", 40),
        ("suggestion", "Suggestion d'amélioration", "Improvement suggestion", 50),
        ("autre", "Autre demande", "Other request", 90),
    ):
        # Bound parameters, not interpolation: a label as ordinary as
        # "Suggestion d'amélioration" carries an apostrophe that ends the SQL string.
        op.execute(
            sa.text(
                "INSERT INTO support_categorie (code, libelle, libelle_en, ordre) "
                "SELECT :code, :libelle, :libelle_en, :ordre "
                "WHERE NOT EXISTS (SELECT 1 FROM support_categorie WHERE code = :code)"
            ).bindparams(code=code, libelle=libelle, libelle_en=libelle_en, ordre=ordre)
        )

    # Row level security: the platform enables it on every table, and a table left
    # without it is the hole an audit finds. Access is granted through the API's own
    # role, as everywhere else in this schema.
    for table in ("support_fil", "support_message", "support_categorie"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON {table} FROM anon")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS support_message")
    op.execute("DROP TABLE IF EXISTS support_fil")
    op.execute("DROP TABLE IF EXISTS support_categorie")
    op.execute("DROP SEQUENCE IF EXISTS support_reference_seq")
