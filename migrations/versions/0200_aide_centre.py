# ruff: noqa: E501 - migrations carry long SQL lines
"""The help centre: one corpus, two scopes, no second catalogue.

The platform ships ten surfaces and none of them can answer "how do I do this".
What exists today is scattered: a 604-line Methodologie.tsx in the direction app,
four InfoTip components, and nothing at all in the controller, which is the one
place a volunteer stands alone in front of a queue.

The decision this migration encodes: **the central desk and the per-application
help centre are the same corpus, filtered.** A second catalogue would drift from
the first within a month, and the reader would find the stale one.

Four things shape the schema.

**The editor and the client never share a row.** Column ``cote`` splits them,
RLS FORCE enforces it, and an article on the editor side is simply never
distributed to a client database: in the base a client application connects to,
the row does not exist. That is the same guarantee that protects member data, and
it is stronger than any application guard.

**A republished catalogue must not crush local work.** Column ``origine`` tells an
editor article from one an organisation wrote. Redistribution touches only
``origine = 'editeur'``. What an organisation wants hidden or reordered goes to
``aide_reglage_local``, keyed on the logical key rather than the identifier,
because identifiers differ from one database to the next.

**Help must filter exactly like the menu it documents.** Columns
``permission_requise`` and ``module_requis`` mirror the NAV registry and the
subscribed modules, and the filter is applied server side. Filtering in the
browser would serve a stale catalogue from the cached session the moment someone's
rights change.

**Accents are folded with translate(), never unaccent().** Migration 0191 already
wrote down why: that function comes from an extension a fresh database does not
necessarily carry, and a migration that depends on one fails on exactly the
deployment that matters, a base provisioned for a new client.

Revision ID: 0200_aide_centre
Revises: 0199_licence_modules
Create Date: 2026-08-25
"""
from __future__ import annotations

from alembic import op

revision = "0200_aide_centre"
down_revision = "0199_licence_modules"
branch_labels = None
depends_on = None

#: The ten real surfaces, plus one that is not a surface at all. Deliberately a
#: CHECK and not a foreign key to application(code): that table is the sellable
#: catalogue and knows seven codes, while help also covers the public site, the
#: console and the client portal, which are not sold as modules.
#:
#: "transverse" carries what belongs to no single application: signing in, two
#: factor authentication, personal data rights. Such an article has to live
#: somewhere, and filing it under one application would hide it from the nine
#: others, where the reader is just as likely to be looking for it. The read API
#: therefore always adds transverse articles to whichever application is asked for.
SURFACES = (
    "back-office", "collaboration", "pilotage", "direction", "controleur",
    "web-membre", "mobile-membre", "portail", "site", "console",
    "transverse",
)

#: Accent folding, identical to the one migration 0191 settled on. The query side
#: must fold the same way, otherwise a search for "presence" misses "présence".
ACCENTUES = "ÉÈÊËéèêëÀÂÁàâáÎÏîïÔÖÓôöóÙÛÜùûüÇç"
PLATS = "EEEEeeeeAAAaaaIIiiOOOoooUUUuuuCc"


def _plie(colonne: str) -> str:
    """SQL that folds one column's accents before it is tokenised."""
    return f"translate(coalesce({colonne}, ''), '{ACCENTUES}', '{PLATS}')"


def upgrade() -> None:
    surfaces = ", ".join(f"'{code}'" for code in SURFACES)

    # -- Rubrics ------------------------------------------------------------
    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS aide_rubrique (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            code text NOT NULL UNIQUE,
            application_code text NOT NULL,
            titre text NOT NULL,
            titre_en text,
            description text NOT NULL DEFAULT '',
            ordre integer NOT NULL DEFAULT 50,
            cote text NOT NULL DEFAULT 'client',
            origine text NOT NULL DEFAULT 'editeur',
            actif boolean NOT NULL DEFAULT true,
            cree_le timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT aide_rubrique_surface CHECK (application_code IN ({surfaces})),
            CONSTRAINT aide_rubrique_cote CHECK (cote IN ('client', 'editeur')),
            CONSTRAINT aide_rubrique_origine CHECK (origine IN ('editeur', 'organisation'))
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS aide_rubrique_surface_idx "
        "ON aide_rubrique (application_code, ordre) WHERE actif")

    # -- Articles -----------------------------------------------------------
    #
    # The unique key is (cle, langue) rather than a slug: the logical key is what
    # ties a French article to its English twin and what survives redistribution,
    # while an identifier does not travel between databases.
    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS aide_article (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            cle text NOT NULL,
            langue text NOT NULL DEFAULT 'fr',
            rubrique_id uuid NOT NULL REFERENCES aide_rubrique(id) ON DELETE RESTRICT,
            slug text NOT NULL,
            titre text NOT NULL,
            extrait text NOT NULL DEFAULT '',
            statut text NOT NULL DEFAULT 'brouillon',
            visibilite text NOT NULL DEFAULT 'membres',
            cote text NOT NULL DEFAULT 'client',
            origine text NOT NULL DEFAULT 'editeur',
            application_code text NOT NULL,
            permission_requise text,
            module_requis text,
            ordre integer NOT NULL DEFAULT 50,
            publie_le timestamptz,
            redige_par uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            redige_par_editeur text,
            cree_le timestamptz NOT NULL DEFAULT now(),
            maj_le timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT aide_article_cle_langue UNIQUE (cle, langue),
            CONSTRAINT aide_article_langue CHECK (langue IN ('fr', 'en')),
            CONSTRAINT aide_article_statut CHECK (statut IN ('brouillon', 'publie', 'archive')),
            CONSTRAINT aide_article_visibilite CHECK (visibilite IN ('public', 'membres', 'gouvernance')),
            CONSTRAINT aide_article_cote CHECK (cote IN ('client', 'editeur')),
            CONSTRAINT aide_article_origine CHECK (origine IN ('editeur', 'organisation')),
            CONSTRAINT aide_article_surface CHECK (application_code IN ({surfaces})),
            -- An editor article carries no author from the client database: the
            -- operator who wrote it has no row in utilisateur there, and the
            -- foreign key would refuse the publication.
            CONSTRAINT aide_article_auteur_editeur
                CHECK (origine <> 'editeur' OR redige_par IS NULL),
            CONSTRAINT aide_article_publie_date
                CHECK (statut <> 'publie' OR publie_le IS NOT NULL)
        )
        """
    )

    # The search vector is generated by the database rather than maintained by a
    # trigger: a trigger can be forgotten on a bulk update, and the column then
    # silently stops matching what the article says.
    op.execute(
        f"""
        ALTER TABLE aide_article
        ADD COLUMN IF NOT EXISTS recherche tsvector
        GENERATED ALWAYS AS (
            setweight(to_tsvector('french', {_plie('titre')}), 'A')
            || setweight(to_tsvector('french', {_plie('extrait')}), 'B')
            || setweight(to_tsvector('french', coalesce(cle, '')), 'C')
        ) STORED
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS aide_article_recherche_idx ON aide_article USING GIN (recherche)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS aide_article_liste_idx "
        "ON aide_article (application_code, cote, statut, ordre)")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS aide_article_slug_idx "
        "ON aide_article (application_code, langue, slug)")

    # -- Published versions -------------------------------------------------
    #
    # The body lives in typed blocks, never in free HTML and never in Markdown
    # rendered raw. The reference project stores Markdown and prints it verbatim:
    # its readers see the asterisks. Typed blocks also let the renderer stay a
    # short component instead of a parser.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aide_article_version (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            article_id uuid NOT NULL REFERENCES aide_article(id) ON DELETE CASCADE,
            version integer NOT NULL,
            blocs jsonb NOT NULL,
            empreinte text NOT NULL DEFAULT '',
            notes text NOT NULL DEFAULT '',
            publie_le timestamptz,
            publie_par uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            cree_le timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT aide_version_unique UNIQUE (article_id, version),
            CONSTRAINT aide_version_blocs_liste CHECK (jsonb_typeof(blocs) = 'array')
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS aide_version_article_idx "
        "ON aide_article_version (article_id, version DESC)")

    # -- Screen anchors -----------------------------------------------------
    #
    # This is what turns a catalogue into help: the screen you are on knows which
    # article describes it. The reference project never had it, and its readers
    # had to search for a page they were already looking at.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aide_ancrage (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            article_id uuid NOT NULL REFERENCES aide_article(id) ON DELETE CASCADE,
            application_code text NOT NULL,
            cle_ecran text NOT NULL,
            position integer NOT NULL DEFAULT 50,
            est_principal boolean NOT NULL DEFAULT false,
            cree_le timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT aide_ancrage_unique UNIQUE (cle_ecran, article_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS aide_ancrage_ecran_idx ON aide_ancrage (cle_ecran, position)")
    # One principal article per screen: two would make the contextual button open
    # whichever the planner happened to return first.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS aide_ancrage_principal_idx "
        "ON aide_ancrage (cle_ecran) WHERE est_principal")

    # -- Local overrides ----------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aide_reglage_local (
            cle_article text PRIMARY KEY,
            masque boolean NOT NULL DEFAULT false,
            ordre_local integer,
            motif text NOT NULL DEFAULT '',
            par uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            le timestamptz NOT NULL DEFAULT now()
        )
        """
    )

    # -- Usage --------------------------------------------------------------
    #
    # One event table, not three counters. A counter nothing increments is worse
    # than no counter: the reference shows a view count stuck at zero and someone
    # will eventually plan the editorial backlog with it.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aide_usage (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            type text NOT NULL,
            application text NOT NULL DEFAULT '',
            cle_ecran text NOT NULL DEFAULT '',
            article_id uuid REFERENCES aide_article(id) ON DELETE SET NULL,
            requete text NOT NULL DEFAULT '',
            resultats integer,
            utile boolean,
            commentaire text NOT NULL DEFAULT '',
            utilisateur_id uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            langue text NOT NULL DEFAULT 'fr',
            cree_le timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT aide_usage_type
                CHECK (type IN ('ouverture', 'recherche', 'lecture', 'avis', 'escalade'))
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS aide_usage_type_idx ON aide_usage (type, cree_le DESC)")
    # The one query that says what to write next: searches that found nothing.
    op.execute(
        "CREATE INDEX IF NOT EXISTS aide_usage_sans_resultat_idx "
        "ON aide_usage (cree_le DESC) WHERE type = 'recherche' AND resultats = 0")

    # -- Distribution journal (editor database only) ------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aide_publication (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            organisation_id uuid NOT NULL REFERENCES organisation_cliente(id) ON DELETE CASCADE,
            version_catalogue text NOT NULL DEFAULT '',
            articles integer NOT NULL DEFAULT 0,
            rubriques integer NOT NULL DEFAULT 0,
            publie_le timestamptz NOT NULL DEFAULT now(),
            publie_par text NOT NULL DEFAULT '',
            resultat jsonb NOT NULL DEFAULT '{}'::jsonb
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS aide_publication_org_idx "
        "ON aide_publication (organisation_id, publie_le DESC)")

    # -- Support handover ---------------------------------------------------
    #
    # Strictly technical context, frozen at the moment the request opens. No
    # member identifier, no role, no perimeter: widening this would turn support
    # into a standing right to look at the members of every organisation.
    for colonne, type_sql in (
        ("cle_ecran", "text"),
        ("article_cle", "text"),
        ("requete_recherche", "text"),
        ("version_application", "text"),
    ):
        op.execute(f"ALTER TABLE support_fil ADD COLUMN IF NOT EXISTS {colonne} {type_sql}")

    # -- Row level security -------------------------------------------------
    #
    # FORCE as well as ENABLE: the API connects as the schema owner, and an owner
    # bypasses its own policies unless the table forces them. That is the exact
    # gap an audit finds, and the one that would let a client request read an
    # editor article.
    for table in (
        "aide_rubrique", "aide_article", "aide_article_version", "aide_ancrage",
        "aide_reglage_local", "aide_usage", "aide_publication",
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON {table} FROM anon")
        op.execute(f"REVOKE ALL ON {table} FROM authenticated")

    # Reading the client side is open to the application role; the editor side is
    # readable only inside a transaction that has declared itself as the editor,
    # which only the editor dependency does. Note there is no SECURITY DEFINER
    # function anywhere here: the reference project learned the hard way that such
    # a function escapes RLS and had been exposing the titles of internal guides.
    for table in ("aide_rubrique", "aide_article"):
        op.execute(f"DROP POLICY IF EXISTS {table}_lecture ON {table}")
        op.execute(
            f"""
            CREATE POLICY {table}_lecture ON {table} FOR SELECT
            USING (
                cote = 'client'
                OR coalesce(current_setting('adsum.cote', true), '') = 'editeur'
            )
            """
        )
        op.execute(f"DROP POLICY IF EXISTS {table}_ecriture ON {table}")
        op.execute(
            f"""
            CREATE POLICY {table}_ecriture ON {table} FOR ALL
            USING (
                cote = 'client'
                OR coalesce(current_setting('adsum.cote', true), '') = 'editeur'
            )
            WITH CHECK (
                cote = 'client'
                OR coalesce(current_setting('adsum.cote', true), '') = 'editeur'
            )
            """
        )

    # The remaining tables carry no side of their own: they hang off an article
    # and inherit its reach through the foreign key. A permissive policy here
    # would be a hole, so each one is restricted to rows whose article is visible.
    op.execute("DROP POLICY IF EXISTS aide_version_portee ON aide_article_version")
    op.execute(
        """
        CREATE POLICY aide_version_portee ON aide_article_version FOR ALL
        USING (EXISTS (SELECT 1 FROM aide_article a WHERE a.id = article_id))
        WITH CHECK (EXISTS (SELECT 1 FROM aide_article a WHERE a.id = article_id))
        """
    )
    op.execute("DROP POLICY IF EXISTS aide_ancrage_portee ON aide_ancrage")
    op.execute(
        """
        CREATE POLICY aide_ancrage_portee ON aide_ancrage FOR ALL
        USING (EXISTS (SELECT 1 FROM aide_article a WHERE a.id = article_id))
        WITH CHECK (EXISTS (SELECT 1 FROM aide_article a WHERE a.id = article_id))
        """
    )
    # Usage, local settings and the publication journal are written by the server
    # and read by the console; they carry no editor content, so the policy is open
    # to the application role and closed to everyone else by the REVOKE above.
    for table in ("aide_reglage_local", "aide_usage", "aide_publication"):
        op.execute(f"DROP POLICY IF EXISTS {table}_service ON {table}")
        op.execute(f"CREATE POLICY {table}_service ON {table} FOR ALL USING (true) WITH CHECK (true)")


def downgrade() -> None:
    for colonne in ("cle_ecran", "article_cle", "requete_recherche", "version_application"):
        op.execute(f"ALTER TABLE support_fil DROP COLUMN IF EXISTS {colonne}")
    for table in (
        "aide_publication", "aide_usage", "aide_reglage_local", "aide_ancrage",
        "aide_article_version", "aide_article", "aide_rubrique",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table}")
