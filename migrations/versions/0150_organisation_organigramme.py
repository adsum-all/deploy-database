# ruff: noqa: E501 - migrations carry long SQL lines
"""Organisation chart module: versioned, editable, publishable org hierarchy.

The organigramme is a real business module, not a static picture. It stores an
explicit graph of nodes (people, structures, groups) and typed links (functional
reporting, direct coordination, supervision, transversal follow-up, tribal
responsibility, assistance), under a draft/publish version workflow with a full
change log. The graph is first BUILT from the real data (functions, members,
commissions, tribes, patriarchs), then can be edited, validated and published;
members only ever see the published version.

Four tables:
- organisation_version: a draft or published snapshot of the whole chart.
- organisation_node: one card of a version (person/structure/group).
- organisation_link: one typed relation between two nodes of a version.
- organisation_changelog: an immutable audit trail of every edit.

Revision ID: 0150_organisation_org
Revises: 0149_categorie_attribution
Create Date: 2026-07-18
"""
from __future__ import annotations

from alembic import op

revision = "0150_organisation_org"
down_revision = "0149_categorie_attribution"
branch_labels = None
depends_on = None

_STATUTS_VERSION = ("brouillon", "publie", "archive")
_TYPES_NOEUD = ("personne", "structure", "groupe")
_TYPES_LIEN = (
    "hierarchique",        # functional authority / N+1, solid vertical arrow
    "coordination",        # direct coordination, solid horizontal arrow
    "supervision",         # direct supervision of a particular branch, angled
    "suivi_transversal",   # transversal follow-up, dashed, no subordination
    "responsabilite_tribu",  # a patriarch is responsible for a tribe
    "assistance",          # assistant / secretary of a role
)


def upgrade() -> None:
    op.execute(
        "CREATE TABLE IF NOT EXISTS organisation_version ("
        "id uuid PRIMARY KEY DEFAULT gen_random_uuid(), "
        "libelle text NOT NULL, "
        f"statut text NOT NULL DEFAULT 'brouillon' CHECK (statut IN ({', '.join(repr(s) for s in _STATUTS_VERSION)})), "
        "note text, "
        "cree_par uuid REFERENCES utilisateur(id) ON DELETE SET NULL, "
        "cree_le timestamptz NOT NULL DEFAULT now(), "
        "publie_le timestamptz, "
        "publie_par uuid REFERENCES utilisateur(id) ON DELETE SET NULL, "
        "source_version_id uuid REFERENCES organisation_version(id) ON DELETE SET NULL"
        ")"
    )
    # At most one published version at a time (partial unique index).
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_organisation_version_publiee ON organisation_version ((statut)) WHERE statut = 'publie'")

    op.execute(
        "CREATE TABLE IF NOT EXISTS organisation_node ("
        "id uuid PRIMARY KEY DEFAULT gen_random_uuid(), "
        "version_id uuid NOT NULL REFERENCES organisation_version(id) ON DELETE CASCADE, "
        f"type_noeud text NOT NULL DEFAULT 'structure' CHECK (type_noeud IN ({', '.join(repr(t) for t in _TYPES_NOEUD)})), "
        "cle text, "                       # stable key within the version (e.g. 'fondateur', 'tribu:<id>')
        "nom text NOT NULL, "
        "sous_titre text, "                # e.g. the function label or scope
        "membre_id uuid REFERENCES membre(id) ON DELETE SET NULL, "
        "fonction_cle text, "
        "categorie text, "                 # titre / fonction_speciale / fonction / fonction_particuliere
        "unite_type text, "                # commission / coordination / intendance / tribu / college / groupe
        "unite_id uuid, "
        "effectif integer, "
        "statut text NOT NULL DEFAULT 'actif', "  # actif / vacant / attente / archive
        "pos_x double precision, "
        "pos_y double precision, "
        "ordre integer NOT NULL DEFAULT 100, "
        "meta jsonb NOT NULL DEFAULT '{}'::jsonb, "
        "actif boolean NOT NULL DEFAULT true"
        ")"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_organisation_node_version ON organisation_node (version_id, actif)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_organisation_node_membre ON organisation_node (membre_id)")

    op.execute(
        "CREATE TABLE IF NOT EXISTS organisation_link ("
        "id uuid PRIMARY KEY DEFAULT gen_random_uuid(), "
        "version_id uuid NOT NULL REFERENCES organisation_version(id) ON DELETE CASCADE, "
        "source_id uuid NOT NULL REFERENCES organisation_node(id) ON DELETE CASCADE, "
        "cible_id uuid NOT NULL REFERENCES organisation_node(id) ON DELETE CASCADE, "
        f"type_lien text NOT NULL DEFAULT 'hierarchique' CHECK (type_lien IN ({', '.join(repr(t) for t in _TYPES_LIEN)})), "
        "libelle text, "
        "actif boolean NOT NULL DEFAULT true, "
        "CONSTRAINT organisation_link_pas_de_boucle_directe CHECK (source_id <> cible_id)"
        ")"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_organisation_link_version ON organisation_link (version_id, actif)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_organisation_link_source ON organisation_link (source_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_organisation_link_cible ON organisation_link (cible_id)")

    op.execute(
        "CREATE TABLE IF NOT EXISTS organisation_changelog ("
        "id uuid PRIMARY KEY DEFAULT gen_random_uuid(), "
        "version_id uuid REFERENCES organisation_version(id) ON DELETE CASCADE, "
        "acteur_id uuid REFERENCES utilisateur(id) ON DELETE SET NULL, "
        "action text NOT NULL, "
        "cible_type text, "
        "cible_id uuid, "
        "avant jsonb, "
        "apres jsonb, "
        "cree_le timestamptz NOT NULL DEFAULT now()"
        ")"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_organisation_changelog_version ON organisation_changelog (version_id, cree_le DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS organisation_changelog")
    op.execute("DROP TABLE IF EXISTS organisation_link")
    op.execute("DROP TABLE IF EXISTS organisation_node")
    op.execute("DROP TABLE IF EXISTS organisation_version")
