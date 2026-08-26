# ruff: noqa: E501 - migrations carry long SQL lines
"""The help articles, all surfaces.

The text lives in ``migrations/donnees/aide/*.json``, one file per surface, and this
revision loads whatever it finds there. Three reasons, none of them convenience.

Editorial content is not code. A revision carrying six hundred lines of prose would
fail the repository's five-hundred-line rule, would be unreadable in review, and
would force whoever fixes a typo to edit SQL.

Correcting a sentence must not need a new revision. The load is an upsert on the
logical key, so re-running it after an editorial pass updates what changed and
leaves the rest alone.

And what an organisation added itself must survive. The upsert is restricted to
``origine = 'editeur'``: a row written locally is never touched, whatever the
catalogue says.

The controller comes first in the catalogue, and deliberately: it is the front
where the absence of help costs the most, a volunteer alone before a queue, often on
a borrowed phone, sometimes with no network, and the only one registering no service
worker. One of its five articles documents a behaviour that loses attendances in
silence and that nothing in the interface announces: the queue pushes only what the
signed-in controller recorded, so handing the post over before it empties leaves
those entries stuck.

No article names a level of the hierarchy. Those words are configurable per
organisation, and an article that hard-codes one is wrong from its first sentence
for whoever renamed it.

Every article was checked before being written here: known surface, known block
types, no hard-coded vocabulary that an organisation may rename, no em-dash, no
duplicate key. What failed a check was dropped rather than published.

Revision ID: 0201_aide_contenu
Revises: 0200_aide_centre
Create Date: 2026-08-26
"""
from __future__ import annotations

import json
import pathlib

import sqlalchemy as sa
from alembic import op

revision = "0201_aide_contenu"
down_revision = "0200_aide_centre"
branch_labels = None
depends_on = None

#: Resolved from this file rather than from the working directory: alembic is run
#: from wherever the operator happens to stand, and a relative path would find the
#: articles on one machine and nothing on another.
DONNEES = pathlib.Path(__file__).resolve().parent.parent / "donnees" / "aide"


def upgrade() -> None:
    for fichier in sorted(DONNEES.glob("*.json")):
        charge = json.loads(fichier.read_text(encoding="utf-8"))
        for rubrique in charge.get("rubriques", []):
            _poser_rubrique(rubrique)
        for article in charge.get("articles", []):
            _poser_article(article)


def _poser_rubrique(rubrique: dict) -> None:
    op.execute(
        sa.text(
            "INSERT INTO aide_rubrique"
            " (code, application_code, titre, titre_en, description, ordre, cote, origine)"
            " VALUES (:code, :app, :titre, :titre_en, :description, :ordre, :cote, 'editeur')"
            " ON CONFLICT (code) DO UPDATE SET"
            "   titre = EXCLUDED.titre, titre_en = EXCLUDED.titre_en,"
            "   description = EXCLUDED.description, ordre = EXCLUDED.ordre"
            " WHERE aide_rubrique.origine = 'editeur'"
        ).bindparams(
            code=rubrique["code"], app=rubrique["application_code"],
            titre=rubrique["titre"], titre_en=rubrique.get("titre_en"),
            description=rubrique.get("description", ""),
            ordre=int(rubrique.get("ordre", 50)),
            cote=rubrique.get("cote", "client"),
        )
    )


def _poser_article(article: dict) -> None:
    # The article row first. ON CONFLICT on (cle, langue) rather than on the id:
    # identifiers differ from one database to the next, the logical key does not.
    op.execute(
        sa.text(
            "INSERT INTO aide_article"
            " (cle, langue, rubrique_id, slug, titre, extrait, statut, visibilite,"
            "  cote, origine, application_code, permission_requise, module_requis,"
            "  ordre, publie_le, redige_par_editeur)"
            " SELECT :cle, 'fr', r.id, :slug, :titre, :extrait, 'publie', :visibilite,"
            "        :cote, 'editeur', :app, :permission, :module, :ordre, now(), 'editeur'"
            " FROM aide_rubrique r WHERE r.code = :rubrique"
            " ON CONFLICT (cle, langue) DO UPDATE SET"
            "   titre = EXCLUDED.titre, extrait = EXCLUDED.extrait,"
            "   slug = EXCLUDED.slug, ordre = EXCLUDED.ordre,"
            "   permission_requise = EXCLUDED.permission_requise,"
            "   module_requis = EXCLUDED.module_requis, maj_le = now()"
            " WHERE aide_article.origine = 'editeur'"
        ).bindparams(
            cle=article["cle"], slug=article["slug"], titre=article["titre"],
            extrait=article.get("extrait", ""), rubrique=article["rubrique"],
            app=article["application_code"], ordre=int(article.get("ordre", 50)),
            cote=article.get("cote", "client"),
            visibilite=article.get("visibilite", "membres"),
            permission=article.get("permission_requise"),
            module=article.get("module_requis"),
        )
    )

    # Then the body, as a new version rather than an edit of the old one. What was
    # published stays as it was published: an article that changes under a reader
    # who was told to follow it is worse than one that is simply out of date.
    op.execute(
        sa.text(
            "INSERT INTO aide_article_version (article_id, version, blocs, notes, publie_le)"
            " SELECT a.id, coalesce(max(v.version), 0) + 1, CAST(:blocs AS jsonb),"
            "        'catalogue editeur', now()"
            " FROM aide_article a LEFT JOIN aide_article_version v ON v.article_id = a.id"
            " WHERE a.cle = :cle AND a.langue = 'fr'"
            " GROUP BY a.id"
            # Nothing to do when the body has not moved: a fresh version on every
            # run would grow the table without recording a single change.
            " HAVING NOT EXISTS ("
            "   SELECT 1 FROM aide_article_version d"
            "   WHERE d.article_id = a.id AND d.blocs = CAST(:blocs AS jsonb))"
        ).bindparams(
            cle=article["cle"],
            blocs=json.dumps(article["blocs"], ensure_ascii=False),
        )
    )

    if not article.get("cle_ecran"):
        return
    op.execute(
        sa.text(
            "INSERT INTO aide_ancrage (article_id, application_code, cle_ecran, position, est_principal)"
            " SELECT a.id, :app, :ecran, :ordre, false FROM aide_article a"
            " WHERE a.cle = :cle AND a.langue = 'fr'"
            " ON CONFLICT (cle_ecran, article_id) DO NOTHING"
        ).bindparams(
            cle=article["cle"], app=article["application_code"],
            ecran=article["cle_ecran"], ordre=int(article.get("ordre", 50)),
        )
    )


def downgrade() -> None:
    for fichier in sorted(DONNEES.glob("*.json")):
        charge = json.loads(fichier.read_text(encoding="utf-8"))
        for article in charge.get("articles", []):
            op.execute(
                sa.text("DELETE FROM aide_article WHERE cle = :cle AND origine = 'editeur'")
                .bindparams(cle=article["cle"]))
        for rubrique in charge.get("rubriques", []):
            # RESTRICT on the article foreign key means a rubric still holding a
            # locally written article refuses to go, which is the intended answer.
            op.execute(
                sa.text("DELETE FROM aide_rubrique WHERE code = :code AND origine = 'editeur'"
                        " AND NOT EXISTS (SELECT 1 FROM aide_article a WHERE a.rubrique_id = aide_rubrique.id)")
                .bindparams(code=rubrique["code"]))
