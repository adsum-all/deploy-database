"""What the help articles must hold true, checked on the data rather than on the SQL.

The text lives in ``migrations/donnees/aide/*.json`` so it can be corrected without
touching a revision. That freedom needs a guard: nothing here goes through code
review the way a migration does, and a sentence naming a screen that no longer
exists is worse than no article at all, because it sends the reader looking for it.

Two rules matter more than the rest.

**No article names a level of the hierarchy.** Those words are configurable per
organisation, and an article writing one in full is wrong from its first sentence
for whoever renamed it. This is not style: it is the difference between a help
centre that survives being sold to a second customer and one that does not.

**An editor article never claims a client surface.** The side of an article decides
whether it is ever distributed to a client database. A console guide filed under a
client application would travel with the catalogue, which is the one thing the whole
cote column exists to prevent.
"""
from __future__ import annotations

import json
import pathlib
import re

import pytest

DONNEES = pathlib.Path(__file__).resolve().parent.parent / "migrations" / "donnees" / "aide"

SURFACES = {
    "back-office", "collaboration", "pilotage", "direction", "controleur",
    "web-membre", "mobile-membre", "portail", "site", "console", "transverse",
}
BLOCS = {"paragraphe", "etapes", "points", "avertissement", "formule", "lien_ecran"}
VISIBILITES = {"public", "membres", "gouvernance"}
COTES = {"client", "editeur"}

#: Configurable per organisation. See migration 0185 and the org_mot_* settings.
FIGES = re.compile(r"\b(tribus?|commissions?|coordinations?|intendances?)\b", re.IGNORECASE)
#: The product name belongs in a title, never in a sentence addressed to a reader
#: whose organisation may have rebranded the platform entirely.
MARQUE = re.compile(r"\bADSUM\b")
# Ecrits en echappement : poser les caracteres eux-memes ferait remplacer la
# regle par le garde de typographie, qui ne peut pas savoir qu ils sont ici la
# donnee a detecter et non du texte. Elle se mettrait alors a refuser le moindre
# trait d union.
TIRETS = re.compile("[" + chr(0x2014) + chr(0x2013) + "]")
#: application.section, lower case, as the navigation registries write it.
CLE_ECRAN = re.compile(r"^[a-z0-9-]+\.[a-z0-9-]+$")


def _fichiers() -> list[pathlib.Path]:
    return sorted(DONNEES.glob("*.json"))


def _articles() -> list[tuple[str, dict]]:
    resultat = []
    for fichier in _fichiers():
        charge = json.loads(fichier.read_text(encoding="utf-8"))
        for article in charge.get("articles", []):
            resultat.append((fichier.name, article))
    return resultat


def _rubriques() -> list[tuple[str, dict]]:
    resultat = []
    for fichier in _fichiers():
        charge = json.loads(fichier.read_text(encoding="utf-8"))
        for rubrique in charge.get("rubriques", []):
            resultat.append((fichier.name, rubrique))
    return resultat


def _texte(article: dict) -> str:
    morceaux = [article.get("titre", ""), article.get("extrait", "")]
    for bloc in article.get("blocs", []):
        morceaux.append(bloc.get("texte", ""))
        morceaux.extend(bloc.get("elements", []) or [])
    return "\n".join(m for m in morceaux if m)


def test_il_y_a_du_contenu():
    """Une suite qui ne vérifie rien passe toujours."""
    assert _articles(), "aucun article : les contrôles suivants ne prouveraient rien"


def test_chaque_article_vise_une_surface_connue():
    for fichier, article in _articles():
        assert article["application_code"] in SURFACES, f"{fichier}: {article['cle']}"


def test_chaque_article_a_une_rubrique_declaree():
    """Sans sa rubrique, l'insertion ne rend aucune ligne et l'article disparait."""
    for fichier in _fichiers():
        charge = json.loads(fichier.read_text(encoding="utf-8"))
        codes = {r["code"] for r in charge.get("rubriques", [])}
        for article in charge.get("articles", []):
            assert article["rubrique"] in codes, (
                f"{fichier.name}: {article['cle']} vise la rubrique "
                f"{article['rubrique']}, qui n'est pas declaree")


def test_aucune_rubrique_ne_promet_une_reponse_qu_elle_n_a_pas():
    for fichier in _fichiers():
        charge = json.loads(fichier.read_text(encoding="utf-8"))
        utilisees = {a["rubrique"] for a in charge.get("articles", [])}
        for rubrique in charge.get("rubriques", []):
            assert rubrique["code"] in utilisees, (
                f"{fichier.name}: la rubrique {rubrique['code']} est vide")


def test_aucune_cle_n_est_utilisee_deux_fois():
    vues: dict[str, str] = {}
    for fichier, article in _articles():
        cle = article["cle"]
        assert cle not in vues, f"{cle} present dans {vues[cle]} et {fichier}"
        vues[cle] = fichier


def test_chaque_article_porte_au_moins_un_bloc():
    for fichier, article in _articles():
        assert article.get("blocs"), f"{fichier}: {article['cle']} n'a aucun bloc"


def test_les_blocs_sont_de_types_connus():
    for fichier, article in _articles():
        for bloc in article["blocs"]:
            assert bloc["type"] in BLOCS, f"{fichier}: {article['cle']}: {bloc['type']}"


def test_une_liste_sans_elements_n_est_pas_une_liste():
    for fichier, article in _articles():
        for bloc in article["blocs"]:
            if bloc["type"] in ("etapes", "points"):
                assert bloc.get("elements"), (
                    f"{fichier}: {article['cle']}: un bloc {bloc['type']} vide")


def test_aucun_article_n_ecrit_un_terme_que_l_organisation_peut_renommer():
    for fichier, article in _articles():
        trouve = FIGES.search(_texte(article))
        assert trouve is None, (
            f"{fichier}: {article['cle']} ecrit « {trouve.group(0) if trouve else ''} », "
            "qui est configurable par organisation")


def test_aucun_article_n_ecrit_la_marque_dans_son_texte():
    for fichier, article in _articles():
        assert MARQUE.search(_texte(article)) is None, (
            f"{fichier}: {article['cle']} nomme la plateforme en dur")


def test_aucun_tiret_cadratin_dans_le_contenu():
    for fichier, article in _articles():
        assert TIRETS.search(_texte(article)) is None, f"{fichier}: {article['cle']}"


def test_les_cles_d_ecran_ont_la_forme_attendue():
    """Une cle mal formee ne correspond a aucune ancre et ouvre un tiroir vide."""
    for fichier, article in _articles():
        ecran = article.get("cle_ecran", "")
        if not ecran:
            continue
        assert CLE_ECRAN.match(ecran), f"{fichier}: {article['cle']}: « {ecran} »"


def test_une_ancre_reste_dans_l_application_de_son_article():
    for fichier, article in _articles():
        ecran = article.get("cle_ecran", "")
        if not ecran or article["application_code"] == "transverse":
            continue
        assert ecran.split(".")[0] == article["application_code"], (
            f"{fichier}: {article['cle']} est range sous "
            f"{article['application_code']} mais ancre sur {ecran}")


def test_un_article_editeur_ne_se_range_jamais_sous_une_surface_cliente():
    """C'est ce que la colonne cote existe pour empecher."""
    for fichier, article in _articles():
        if article.get("cote") == "editeur":
            assert article["application_code"] == "console", (
                f"{fichier}: {article['cle']} est cote editeur sous "
                f"{article['application_code']}")


def test_les_valeurs_de_cote_et_de_visibilite_sont_connues():
    for fichier, article in _articles():
        assert article.get("cote", "client") in COTES, f"{fichier}: {article['cle']}"
        assert article.get("visibilite", "membres") in VISIBILITES, (
            f"{fichier}: {article['cle']}")
    for fichier, rubrique in _rubriques():
        assert rubrique.get("cote", "client") in COTES, f"{fichier}: {rubrique['code']}"


@pytest.mark.parametrize("champ", ["cle", "slug", "titre", "rubrique", "application_code"])
def test_les_champs_obligatoires_ne_sont_jamais_vides(champ):
    for fichier, article in _articles():
        assert str(article.get(champ, "")).strip(), (
            f"{fichier}: un article sans {champ}")
