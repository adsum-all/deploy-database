# ruff: noqa: E501 - migrations carry long SQL lines
"""Institutional identity, commemorative dates and the catholic liturgical calendar.

Builds on 0160 (institution identity in integration_config + date_institutionnelle):
- extends the identity key/value config with the full institutional identity
  (acronym, slogan, descriptions, mission/vision/values, contact, logo/banner,
  socials, founder) so any association can be described without code changes;
- enriches date_institutionnelle into a real "reference date" (year of origin for
  the anniversary count, yearly recurrence, colour, priority, publication status,
  calendar flag, times, media, admin note) that surfaces in the member calendar as
  a non-activity;
- adds reference_couleur, a controlled colour referential reserved to reference
  dates (distinct from activity type colours);
- adds date_liturgique, an administrable catalogue of catholic feasts: fixed feasts
  (month/day) and movable feasts (a key the liturgical engine computes each year).

Revision ID: 0165_identite_calendrier_institutionnel
Revises: 0164_vice_fonctions_interim
Create Date: 2026-07-19
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0165_calendrier_institutionnel"
down_revision = "0164_vice_fonctions_interim"
branch_labels = None
depends_on = None

_LECTURE_TOUS = "ARRAY['super_admin','admin','gestionnaire','direction','controleur','membre']::text[]"
_ECRITURE = "ARRAY['super_admin','admin']::text[]"

# New identity keys (seeded empty; existing org_* keys from 0160 are untouched).
_IDENTITE_NOUVELLES = [
    "org_acronyme", "org_slogan", "org_description_courte", "org_description_longue",
    "org_mission", "org_vision", "org_valeurs", "org_email", "org_telephone", "org_whatsapp",
    "org_adresse", "org_pays", "org_ville", "org_langue", "org_logo_url", "org_banniere_url",
    "org_reseaux", "org_fondateur_membre_id", "org_fondateur_nom", "org_fondateur_type",
    "org_fondation_lieu", "org_texte_historique", "org_source_validee",
]

# Reserved colour referential for reference dates (cle, libelle, hex, categorie, icone).
_COULEURS = [
    ("inst_anniversaire", "Anniversaire institutionnel", "#b6791b", "institution", "cake"),
    ("inst_commemoration", "Commémoration institutionnelle", "#7a1f5a", "institution", "flag"),
    ("inst_priere", "Journée de prière", "#3f5cc4", "institution", "pray"),
    ("inst_reconnaissance", "Journée de reconnaissance", "#0f8a6a", "institution", "hand-heart"),
    ("inst_memoriel", "Date mémorielle", "#5b6470", "institution", "monument"),
    ("inst_saint_patron", "Fête du saint patron", "#c9a227", "institution", "star"),
    ("lit_pascal", "Temps pascal (blanc/or)", "#c9a227", "liturgie", "sun"),
    ("lit_violet", "Avent / Carême", "#7d5ba6", "liturgie", "candle"),
    ("lit_rouge", "Passion / martyrs", "#b23a3a", "liturgie", "flame"),
    ("lit_blanc", "Solennité (blanc/or)", "#c9a227", "liturgie", "crown"),
    ("lit_marial", "Fête mariale", "#3f5cc4", "liturgie", "rose"),
    ("lit_saint", "Fête d'un saint", "#0f8a6a", "liturgie", "halo"),
    ("lit_gris", "Samedi Saint / deuil", "#6b7280", "liturgie", "cloud"),
    ("lit_vert", "Temps ordinaire", "#2f8f5b", "liturgie", "leaf"),
]

# Fixed catholic feasts (cle, nom, mois, jour, rang, couleur).
_FIXES = [
    ("sainte_marie_mere_dieu", "Sainte Marie, Mère de Dieu", 1, 1, "solennite", "lit_marial"),
    ("epiphanie", "Épiphanie du Seigneur", 1, 6, "solennite", "lit_blanc"),
    ("presentation_seigneur", "Présentation du Seigneur", 2, 2, "fete", "lit_blanc"),
    ("saint_joseph", "Saint Joseph, époux de la Vierge Marie", 3, 19, "solennite", "lit_blanc"),
    ("annonciation", "Annonciation du Seigneur", 3, 25, "solennite", "lit_blanc"),
    ("saint_jean_vianney", "Saint Jean-Marie Vianney", 8, 4, "memoire", "lit_saint"),
    ("nativite_jean_baptiste", "Nativité de saint Jean-Baptiste", 6, 24, "solennite", "lit_blanc"),
    ("saints_pierre_paul", "Saints Pierre et Paul, apôtres", 6, 29, "solennite", "lit_rouge"),
    ("saint_benoit", "Saint Benoît, abbé", 7, 11, "fete", "lit_blanc"),
    ("transfiguration", "Transfiguration du Seigneur", 8, 6, "fete", "lit_blanc"),
    ("assomption", "Assomption de la Bienheureuse Vierge Marie", 8, 15, "solennite", "lit_marial"),
    ("nativite_marie", "Nativité de la Bienheureuse Vierge Marie", 9, 8, "fete", "lit_marial"),
    ("croix_glorieuse", "La Croix glorieuse", 9, 14, "fete", "lit_rouge"),
    ("padre_pio", "Saint Pio de Pietrelcina", 9, 23, "memoire", "lit_saint"),
    ("archanges", "Saints Michel, Gabriel et Raphaël, archanges", 9, 29, "fete", "lit_blanc"),
    ("toussaint", "Tous les Saints", 11, 1, "solennite", "lit_blanc"),
    ("defunts", "Commémoration de tous les fidèles défunts", 11, 2, "memoire", "lit_violet"),
    ("immaculee_conception", "Immaculée Conception de la Vierge Marie", 12, 8, "solennite", "lit_marial"),
    ("nativite_seigneur", "Nativité du Seigneur (Noël)", 12, 25, "solennite", "lit_blanc"),
]

# Movable feasts catalogue (cle == liturgical-engine key; nom/rang/couleur mirror liturgie._MOBILE_META).
_MOBILES = [
    ("cendres", "Mercredi des Cendres", "jour", "lit_violet"),
    ("rameaux", "Dimanche des Rameaux", "dimanche", "lit_rouge"),
    ("jeudi_saint", "Jeudi Saint, Cène du Seigneur", "triduum", "lit_blanc"),
    ("vendredi_saint", "Vendredi Saint, Passion du Seigneur", "triduum", "lit_rouge"),
    ("samedi_saint", "Samedi Saint", "triduum", "lit_gris"),
    ("paques", "Dimanche de la Résurrection (Pâques)", "solennite", "lit_pascal"),
    ("lundi_paques", "Lundi de Pâques", "octave", "lit_pascal"),
    ("misericorde", "Dimanche de la Divine Miséricorde", "dimanche", "lit_pascal"),
    ("ascension", "Ascension du Seigneur", "solennite", "lit_blanc"),
    ("pentecote", "Pentecôte", "solennite", "lit_rouge"),
    ("trinite", "Sainte Trinité", "solennite", "lit_blanc"),
    ("saint_sacrement", "Saint-Sacrement (Fête-Dieu)", "solennite", "lit_blanc"),
    ("sacre_coeur", "Sacré-Cœur de Jésus", "solennite", "lit_blanc"),
    ("christ_roi", "Christ, Roi de l'univers", "solennite", "lit_blanc"),
    ("avent", "1er dimanche de l'Avent", "dimanche", "lit_violet"),
]

_SOURCE_LIT = "Calendrier romain général"


def upgrade() -> None:
    # 1) Enrich the reference-date columns on date_institutionnelle.
    for col, ddl in [
        ("annee_origine", "integer"),
        ("repetition_annuelle", "boolean NOT NULL DEFAULT true"),
        ("afficher_calendrier", "boolean NOT NULL DEFAULT true"),
        ("couleur", "text NOT NULL DEFAULT 'inst_commemoration'"),
        ("priorite", "text NOT NULL DEFAULT 'normale'"),
        ("statut", "text NOT NULL DEFAULT 'publie'"),
        ("categorie", "text NOT NULL DEFAULT 'institution'"),
        ("toute_journee", "boolean NOT NULL DEFAULT true"),
        ("heure_debut", "time"),
        ("heure_fin", "time"),
        ("lieu", "text"),
        ("lien", "text"),
        ("image_url", "text"),
        ("message_membre", "text"),
        ("source", "text"),
        ("note_admin", "text"),
        ("maj_par", "uuid"),
        ("maj_le", "timestamptz"),
    ]:
        op.execute(f"ALTER TABLE date_institutionnelle ADD COLUMN IF NOT EXISTS {col} {ddl}")
    op.execute("ALTER TABLE date_institutionnelle DROP CONSTRAINT IF EXISTS date_institutionnelle_priorite_chk")
    op.execute("ALTER TABLE date_institutionnelle ADD CONSTRAINT date_institutionnelle_priorite_chk CHECK (priorite IN ('normale','importante','solennelle'))")
    op.execute("ALTER TABLE date_institutionnelle DROP CONSTRAINT IF EXISTS date_institutionnelle_statut_chk")
    op.execute("ALTER TABLE date_institutionnelle ADD CONSTRAINT date_institutionnelle_statut_chk CHECK (statut IN ('brouillon','publie','archive'))")

    # 2) Reserved colour referential.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS reference_couleur (
            cle text PRIMARY KEY,
            libelle text NOT NULL,
            hex text NOT NULL,
            categorie text NOT NULL DEFAULT 'institution',
            icone text,
            actif boolean NOT NULL DEFAULT true,
            ordre integer NOT NULL DEFAULT 0
        )
        """
    )
    op.execute("ALTER TABLE reference_couleur ENABLE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY reference_couleur_select ON reference_couleur FOR SELECT USING (adsum_current_role() = ANY({_LECTURE_TOUS}))")
    op.execute(f"CREATE POLICY reference_couleur_write ON reference_couleur FOR ALL USING (adsum_current_role() = ANY({_ECRITURE})) WITH CHECK (adsum_current_role() = ANY({_ECRITURE}))")

    # 3) Catholic feast catalogue (fixed + movable).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS date_liturgique (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            cle text UNIQUE NOT NULL,
            nom text NOT NULL,
            type text NOT NULL DEFAULT 'fixe',
            mois integer,
            jour integer,
            cle_mobile text,
            rang text NOT NULL DEFAULT 'memoire',
            categorie text NOT NULL DEFAULT 'liturgie',
            couleur text NOT NULL DEFAULT 'lit_blanc',
            description text,
            source text,
            visibilite text NOT NULL DEFAULT 'membre',
            actif boolean NOT NULL DEFAULT true,
            ordre integer NOT NULL DEFAULT 0,
            cree_le timestamptz NOT NULL DEFAULT now(),
            maj_le timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT date_liturgique_type_chk CHECK (type IN ('fixe','mobile')),
            CONSTRAINT date_liturgique_fixe_chk CHECK (type <> 'fixe' OR (mois BETWEEN 1 AND 12 AND jour BETWEEN 1 AND 31)),
            CONSTRAINT date_liturgique_mobile_chk CHECK (type <> 'mobile' OR cle_mobile IS NOT NULL)
        )
        """
    )
    op.execute("ALTER TABLE date_liturgique ENABLE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY date_liturgique_select ON date_liturgique FOR SELECT USING (adsum_current_role() = ANY({_LECTURE_TOUS}))")
    op.execute(f"CREATE POLICY date_liturgique_write ON date_liturgique FOR ALL USING (adsum_current_role() = ANY({_ECRITURE})) WITH CHECK (adsum_current_role() = ANY({_ECRITURE}))")

    # 4) Seeds.
    bind = op.get_bind()
    for cle in _IDENTITE_NOUVELLES:
        bind.execute(sa.text("INSERT INTO integration_config (cle, valeur) VALUES (:c, '') ON CONFLICT (cle) DO NOTHING"), {"c": cle})

    for ordre, (cle, libelle, hexv, cat, icone) in enumerate(_COULEURS):
        bind.execute(
            sa.text("INSERT INTO reference_couleur (cle, libelle, hex, categorie, icone, ordre) VALUES (:cle, :lib, :hex, :cat, :ic, :ord) ON CONFLICT (cle) DO NOTHING"),
            {"cle": cle, "lib": libelle, "hex": hexv, "cat": cat, "ic": icone, "ord": ordre},
        )

    ordre = 0
    for cle, nom, mois, jour, rang, couleur in _FIXES:
        bind.execute(
            sa.text("INSERT INTO date_liturgique (cle, nom, type, mois, jour, rang, couleur, source, ordre) VALUES (:cle, :nom, 'fixe', :mois, :jour, :rang, :coul, :src, :ord) ON CONFLICT (cle) DO NOTHING"),
            {"cle": cle, "nom": nom, "mois": mois, "jour": jour, "rang": rang, "coul": couleur, "src": _SOURCE_LIT, "ord": ordre},
        )
        ordre += 1
    for cle, nom, rang, couleur in _MOBILES:
        bind.execute(
            sa.text("INSERT INTO date_liturgique (cle, nom, type, cle_mobile, rang, couleur, source, ordre) VALUES (:cle, :nom, 'mobile', :cle, :rang, :coul, :src, :ord) ON CONFLICT (cle) DO NOTHING"),
            {"cle": cle, "nom": nom, "rang": rang, "coul": couleur, "src": _SOURCE_LIT, "ord": ordre},
        )
        ordre += 1


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS date_liturgique")
    op.execute("DROP TABLE IF EXISTS reference_couleur")
    op.execute("DELETE FROM integration_config WHERE cle = ANY(:cles)".replace(":cles", "ARRAY['" + "','".join(_IDENTITE_NOUVELLES) + "']"))
    for col in ["annee_origine", "repetition_annuelle", "afficher_calendrier", "couleur", "priorite", "statut", "categorie", "toute_journee", "heure_debut", "heure_fin", "lieu", "lien", "image_url", "message_membre", "source", "note_admin", "maj_par", "maj_le"]:
        op.execute(f"ALTER TABLE date_institutionnelle DROP COLUMN IF EXISTS {col}")
