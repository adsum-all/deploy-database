# ruff: noqa: E501 - migrations carry long SQL lines
"""The first five help articles: the controller at the door.

The controller application is where the absence of help costs the most. A volunteer
stands alone in front of a queue, often on a borrowed phone, sometimes with no
network, and every second spent guessing is a person waiting. It is also the only
front that registers no service worker, so help fetched over the network would be
missing at exactly the moment it is needed.

Every sentence here is checked against the code rather than imagined.

The fifth article documents a behaviour that loses attendances in silence, and that
nothing in the interface announces. ``queue.ts`` pushes only the entries recorded by
the controller currently signed in, and it does so on purpose: on a shared terminal,
entries typed by one person and synchronised after another had signed in used to be
written to the database under the second one's name. The consequence is that handing
the post over before synchronising leaves the outgoing controller's entries stuck.
That is worth an article of its own.

The vocabulary is deliberately plain. No article names a level of the hierarchy,
because those words are configurable per organisation and an article that hard-codes
one is wrong from its first sentence for whoever renamed it.

Revision ID: 0201_aide_contenu_controleur
Revises: 0200_aide_centre
Create Date: 2026-08-25
"""
from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0201_aide_contenu_controleur"
down_revision = "0200_aide_centre"
branch_labels = None
depends_on = None

RUBRIQUE = "controleur-a-la-porte"

#: The screen keys are the tab identifiers the application already validates,
#: "scan", "manual" and "queue" (App.tsx, TABS_CTRL). Not the French words on the
#: buttons: an anchor written against a label breaks the day the label is
#: translated, and the drawer then opens empty with nothing to signal it.
#:
#: cle, slug, titre, extrait, ecran, ordre, blocs
ARTICLES: tuple[tuple[str, str, str, str, str, int, list[dict[str, object]]], ...] = (
    (
        "controleur-qr-refuse",
        "le-qr-ne-passe-pas",
        "Le QR ne passe pas : passer en saisie manuelle",
        "Ce qu'il faut faire quand le code ne se lit pas, sans faire attendre la file.",
        "controleur.scan",
        10,
        [
            {"type": "paragraphe", "texte": (
                "Un code peut ne pas passer pour trois raisons : l'écran du téléphone est trop "
                "sombre ou fissuré, le code a expiré, ou l'appareil qui scanne a une heure "
                "fausse. Les trois se traitent de la même façon, et il ne faut pas insister "
                "plus de quelques secondes.")},
            {"type": "etapes", "elements": [
                "Toucher « Saisie manuelle ».",
                "Taper le matricule, ou les premières lettres du nom.",
                "Choisir la personne dans la liste proposée.",
                "Valider. Le pointage est enregistré exactement comme s'il avait été scanné.",
            ]},
            {"type": "avertissement", "texte": (
                "Si le message parle d'un code expiré alors que la personne vient de "
                "l'afficher, vérifiez l'heure de l'appareil qui scanne. Une heure fausse "
                "refuse des codes valables, et elle en accepte de périmés.")},
        ],
    ),
    (
        "controleur-verdict-alerte",
        "verdict-alerte",
        "Verdict « alerte » : ce que cela veut dire et ce que je fais",
        "Une alerte n'est pas un refus. Le pointage est pris, et quelqu'un devra regarder.",
        "controleur.scan",
        20,
        [
            {"type": "paragraphe", "texte": (
                "Un verdict « alerte » signale que le dossier de la personne demande une "
                "vérification : une inscription encore incomplète, ou une situation qui "
                "mérite un regard. Le motif est affiché sous le nom.")},
            {"type": "paragraphe", "texte": (
                "Une alerte ne bloque pas l'entrée et n'annule pas le pointage. Votre rôle à "
                "la porte est d'enregistrer la présence, pas de statuer sur un dossier.")},
            {"type": "etapes", "elements": [
                "Lire le motif affiché.",
                "Laisser entrer et passer à la personne suivante.",
                "Signaler le motif à la personne responsable de l'accueil en fin de séance.",
            ]},
            {"type": "avertissement", "texte": (
                "Un refus est autre chose : le pointage n'est alors pas enregistré et l'écran "
                "l'écrit clairement. Dans ce cas, refaites une saisie manuelle avant de "
                "passer au suivant.")},
        ],
    ),
    (
        "controleur-hors-ligne",
        "sans-reseau",
        "Sans réseau, où vont mes pointages",
        "Ils sont gardés sur l'appareil et partent tout seuls au retour du réseau.",
        "controleur.queue",
        30,
        [
            {"type": "paragraphe", "texte": (
                "Chaque pointage est d'abord écrit sur l'appareil, avant tout envoi. Couper le "
                "réseau, recharger la page ou fermer l'application ne perd rien : les "
                "pointages en attente restent et repartent dès que la connexion revient.")},
            {"type": "paragraphe", "texte": (
                "Le compteur « en attente » indique combien de pointages n'ont pas encore été "
                "confirmés par le serveur. Il doit revenir à zéro avant que vous quittiez le "
                "poste.")},
            {"type": "avertissement", "texte": (
                "Un pointage en attente n'est jamais supprimé automatiquement, même après "
                "plusieurs heures. Tant qu'il est là, il doit encore une présence à "
                "quelqu'un.")},
        ],
    ),
    (
        "controleur-file-bloquee",
        "la-file-ne-se-vide-pas",
        "La file ne se vide pas alors que je viens de me reconnecter",
        "Presque toujours parce que les pointages en attente ont été saisis par un autre compte.",
        "controleur.queue",
        40,
        [
            {"type": "paragraphe", "texte": (
                "L'envoi ne concerne que les pointages enregistrés par le compte connecté en "
                "ce moment. C'est voulu : sur un poste partagé, sans cette règle, les "
                "pointages saisis par une personne seraient enregistrés au nom de la "
                "suivante.")},
            {"type": "etapes", "elements": [
                "Vérifier quel compte est connecté.",
                "Si ce n'est pas celui qui a saisi les pointages en attente, se déconnecter.",
                "Reconnecter le compte d'origine : la file repart aussitôt.",
                "Attendre que le compteur « en attente » revienne à zéro.",
            ]},
            {"type": "paragraphe", "texte": (
                "Si le compte est bien le bon et que rien ne part, c'est le réseau. Le "
                "compteur repartira de lui-même, sans aucune manipulation.")},
        ],
    ),
    (
        "controleur-passage-de-poste",
        "passer-le-poste",
        "Passer le poste à un autre contrôleur sans perdre la file",
        "Toujours vider la file avant de changer de compte. C'est la seule règle.",
        "controleur.queue",
        50,
        [
            {"type": "avertissement", "texte": (
                "Changer de compte avec des pointages en attente les laisse bloqués : ils ne "
                "repartiront qu'au retour du compte qui les a saisis.")},
            {"type": "etapes", "elements": [
                "Regarder le compteur « en attente ».",
                "S'il n'est pas à zéro, attendre qu'il y arrive. Rétablir le réseau si besoin.",
                "Une fois à zéro seulement, se déconnecter.",
                "Laisser la personne suivante se connecter avec son propre compte.",
            ]},
            {"type": "paragraphe", "texte": (
                "Si le poste doit changer de main dans l'urgence avec des pointages en "
                "attente, le plus sûr est de laisser l'appareil en l'état et d'en prendre un "
                "second : les pointages bloqués partiront quand le premier contrôleur "
                "reprendra la main.")},
        ],
    ),
)


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO aide_rubrique (code, application_code, titre, titre_en, description, ordre, cote, origine)"
            " SELECT :code, 'controleur', :titre, :titre_en, :description, 10, 'client', 'editeur'"
            " WHERE NOT EXISTS (SELECT 1 FROM aide_rubrique WHERE code = :code)"
        ).bindparams(
            code=RUBRIQUE,
            titre="À la porte",
            titre_en="At the door",
            description="Les cinq situations qui arrivent vraiment pendant un contrôle.",
        )
    )

    for cle, slug, titre, extrait, ecran, ordre, blocs in ARTICLES:
        # Bound parameters throughout: a title as ordinary as "Le QR ne passe pas"
        # is fine, but "l'écran" is not, and an apostrophe ends the SQL string.
        op.execute(
            sa.text(
                "INSERT INTO aide_article"
                " (cle, langue, rubrique_id, slug, titre, extrait, statut, visibilite,"
                "  cote, origine, application_code, ordre, publie_le, redige_par_editeur)"
                " SELECT :cle, 'fr', r.id, :slug, :titre, :extrait, 'publie', 'membres',"
                "        'client', 'editeur', 'controleur', :ordre, now(), 'editeur'"
                " FROM aide_rubrique r WHERE r.code = :rubrique"
                "   AND NOT EXISTS (SELECT 1 FROM aide_article WHERE cle = :cle AND langue = 'fr')"
            ).bindparams(
                cle=cle, slug=slug, titre=titre, extrait=extrait, ordre=ordre,
                rubrique=RUBRIQUE,
            )
        )
        op.execute(
            sa.text(
                "INSERT INTO aide_article_version (article_id, version, blocs, notes, publie_le)"
                " SELECT a.id, 1, CAST(:blocs AS jsonb), 'socle initial', now()"
                " FROM aide_article a"
                " WHERE a.cle = :cle AND a.langue = 'fr'"
                "   AND NOT EXISTS (SELECT 1 FROM aide_article_version v"
                "                   WHERE v.article_id = a.id AND v.version = 1)"
            ).bindparams(cle=cle, blocs=json.dumps(_normaliser(blocs), ensure_ascii=False))
        )
        # The anchor is what makes the help contextual: the screen knows which
        # article answers it, rather than the reader having to search for the page
        # they are already looking at.
        op.execute(
            sa.text(
                "INSERT INTO aide_ancrage (article_id, application_code, cle_ecran, position, est_principal)"
                " SELECT a.id, 'controleur', :ecran, :ordre, false FROM aide_article a"
                " WHERE a.cle = :cle AND a.langue = 'fr'"
                "   AND NOT EXISTS (SELECT 1 FROM aide_ancrage n"
                "                   WHERE n.article_id = a.id AND n.cle_ecran = :ecran)"
            ).bindparams(cle=cle, ecran=ecran, ordre=ordre)
        )


def _normaliser(blocs: list[dict[str, object]]) -> list[dict[str, object]]:
    """Give every block the full shape the reader expects.

    The renderer reads ``texte``, ``elements`` and ``ecran`` on each block. Storing
    them only when non-empty would work today and break the first time a renderer
    stops guarding an absent key.
    """
    return [
        {
            "type": bloc["type"],
            "texte": bloc.get("texte", ""),
            "elements": bloc.get("elements", []),
            "ecran": bloc.get("ecran", ""),
        }
        for bloc in blocs
    ]


def downgrade() -> None:
    for cle, *_ in ARTICLES:
        op.execute(
            sa.text("DELETE FROM aide_article WHERE cle = :cle").bindparams(cle=cle))
    op.execute(
        sa.text("DELETE FROM aide_rubrique WHERE code = :code").bindparams(code=RUBRIQUE))
