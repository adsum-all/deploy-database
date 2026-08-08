# ruff: noqa: E501 - migrations carry long SQL lines
"""Let the direction subscribe to a report instead of remembering to fetch it.

A dashboard is consulted by whoever thinks to open it. The people who most need the
attendance figures, a coordination lead, a commission head, are the ones least likely
to log in on a Monday morning, and a report nobody opens changes nothing.

So a subscription is a stored intention: this report, on this scope, to these people,
at this cadence. The daily job reads the table and sends what is due. That is the
automatic communication channel: the platform reaches out rather than waiting.

Three decisions worth stating.

The scope is stored as the filter set, not as a rendered table. A subscription created
in July must describe August when August comes, and freezing the rows would send the
same figures forever under a fresh date.

Recipients are a list of addresses rather than member links. A report often goes to
somebody who is not a member of the organisation, a treasurer, an auditor, and forcing
a member record to exist for them would create accounts nobody wanted.

The last dispatch is recorded on the row itself. The job compares it against the
cadence, so running the job twice in one day sends nothing twice, which is what makes
an hourly scheduler safe to point at it.

Revision ID: 0193_direction_rapport_planifie
Revises: 0192_declaration_code_membre
Create Date: 2026-08-08
"""
from __future__ import annotations

from alembic import op

revision = "0193_direction_rapport_planifie"
down_revision = "0192_declaration_code_membre"
branch_labels = None
depends_on = None

#: Who may create or change a subscription. A subscription decides what leaves the
#: platform and to whom, so it sits with the roles that answer for that, not with
#: every account able to read a dashboard.
_ECRITURE = "ARRAY['super_admin', 'admin', 'direction']::text[]"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS direction_rapport_planifie (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            libelle text NOT NULL,
            destinataires text[] NOT NULL,
            frequence text NOT NULL,
            dimension text NOT NULL DEFAULT 'commission',
            filtres jsonb NOT NULL DEFAULT '{}'::jsonb,
            actif boolean NOT NULL DEFAULT true,
            dernier_envoi timestamptz,
            dernier_statut text,
            cree_par uuid REFERENCES utilisateur (id) ON DELETE SET NULL,
            cree_le timestamptz NOT NULL DEFAULT now(),
            maj_le timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT direction_rapport_frequence_valide
                CHECK (frequence IN ('quotidien', 'hebdomadaire', 'mensuel')),
            CONSTRAINT direction_rapport_destinataires_non_vide
                CHECK (cardinality(destinataires) BETWEEN 1 AND 20)
        )
        """
    )
    op.execute(
        "COMMENT ON TABLE direction_rapport_planifie IS "
        "'Abonnement à un rapport de direction. Le périmètre est conservé sous forme "
        "de filtres et non de lignes figées, pour que le rapport décrive la période "
        "du jour où il part et non celle du jour où il a été créé.'"
    )

    # The daily job scans for what is due. Partial, so inactive subscriptions cost
    # nothing and the index stays the size of what is actually running.
    op.execute(
        "CREATE INDEX IF NOT EXISTS direction_rapport_planifie_a_envoyer "
        "ON direction_rapport_planifie (frequence, dernier_envoi) WHERE actif"
    )

    # This table names people who are not necessarily members and records what the
    # organisation sends them, so it carries the same row-level policy as every other
    # table on the platform. Reading is open to an authenticated role; only the roles
    # that steer may create or change a subscription.
    #
    # COALESCE rather than a bare NULL comparison, matching the convention of the
    # existing policies: the rule then says what it means instead of working by a
    # property of three-valued logic the next reader has to know.
    op.execute("ALTER TABLE direction_rapport_planifie ENABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS direction_rapport_planifie_lecture ON direction_rapport_planifie")
    op.execute(
        "CREATE POLICY direction_rapport_planifie_lecture ON direction_rapport_planifie FOR SELECT "
        "USING (COALESCE(adsum_current_role(), '') <> '')"
    )

    op.execute("DROP POLICY IF EXISTS direction_rapport_planifie_ecriture ON direction_rapport_planifie")
    op.execute(
        f"CREATE POLICY direction_rapport_planifie_ecriture ON direction_rapport_planifie FOR ALL "
        f"USING (COALESCE(adsum_current_role(), '') = ANY({_ECRITURE})) "
        f"WITH CHECK (COALESCE(adsum_current_role(), '') = ANY({_ECRITURE}))"
    )

    op.execute("REVOKE ALL ON direction_rapport_planifie FROM anon")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS direction_rapport_planifie_a_envoyer")
    op.execute("DROP TABLE IF EXISTS direction_rapport_planifie")
