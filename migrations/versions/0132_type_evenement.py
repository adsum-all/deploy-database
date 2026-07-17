# ruff: noqa: E501 - migrations carry long SQL lines
"""Administrable catalogue of standard event types, each with a UNIQUE colour.

Creates the ``type_evenement`` referential (code, nom, couleur, description, publie)
so the community can manage its recurring events instead of the three hardcoded
types. The colour is unique per type (enforced by a UNIQUE constraint) and is what
the member calendar uses to distinguish events (previously all blue). Events gain a
nullable ``type_evenement_id`` link; an event without a type simply falls back to a
default colour. The 18 standard events are seeded with 18 distinct colours; the list
lives in the database and stays fully editable (never hardcoded in the applications).

Revision ID: 0132_type_evenement
Revises: 0131_tribu_publie
Create Date: 2026-07-13
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0132_type_evenement"
down_revision = "0131_tribu_publie"
branch_labels = None
depends_on = None


# (code ASCII, nom affiche avec accents, couleur unique, description). Order = display order.
_SEED: list[tuple[str, str, str, str]] = [
    ("SEMINAIRE", "SÉMINAIRE", "#2563EB", "Séminaire d'enseignement et de formation spirituelle."),
    ("REPETITION_CHOEUR_KERUBIM", "RÉPÉTITION CHŒUR KERUBIM", "#7C3AED", "Répétition du chœur Kerubim."),
    ("EQUIPE_DANSE_PROPHETIQUE", "ÉQUIPE DE DANSE PROPHÉTIQUE", "#DB2777", "Répétition de l'équipe de danse prophétique."),
    ("ECOLE_DE_MINISTERE", "ÉCOLE DE MINISTÈRE", "#059669", "Cursus de l'école de ministère."),
    ("JEUNE_14_JOURS", "14 JOURS DE JEÛNE ET DE PRIÈRE", "#D97706", "Programme de 14 jours de jeûne et de prière."),
    ("PRIERE_DE_REVELATION", "PRIÈRE DE RÉVÉLATION", "#0891B2", "Veillée ou temps de prière de révélation."),
    ("RENCONTRE_AMES_SEULES", "RENCONTRE DES ÂMES SEULES", "#DC2626", "Rencontre destinée aux personnes célibataires."),
    ("RENCONTRE_DES_COUPLES", "RENCONTRE DES COUPLES", "#E11D48", "Rencontre destinée aux couples."),
    ("PISCINE_DE_BETHESDA", "LA PISCINE DE BETHESDA", "#0D9488", "Rassemblement de guérison et de restauration."),
    ("RDV_ROIS_ET_REINES", "RENDEZ-VOUS DES ROIS ET DES REINES", "#CA8A04", "Rendez-vous des rois et des reines."),
    ("JEUNE_21_JOURS", "21 JOURS DE JEÛNE ET DE PRIÈRE", "#EA580C", "Programme de 21 jours de jeûne et de prière."),
    ("INTERCESSION_COMMUNAUTAIRE", "INTERCESSION COMMUNAUTAIRE", "#4F46E5", "Temps d'intercession communautaire."),
    ("RECOLLECTION", "RECOLLECTION", "#16A34A", "Journée de recollection spirituelle."),
    ("RETRAITE", "RETRAITE", "#9333EA", "Retraite spirituelle."),
    ("SINAI", "SINAÏ", "#B45309", "Rassemblement Sinaï."),
    ("KAIROS", "KAÏROS", "#0284C7", "Rassemblement Kaïros."),
    ("KTO", "KTO", "#65A30D", "Rassemblement KTO."),
    ("TORRENT_DE_KERITH", "TORRENT DE KÉRITH", "#C026D3", "Rassemblement Torrent de Kérith."),
]


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS type_evenement (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            code text NOT NULL UNIQUE,
            nom text NOT NULL UNIQUE,
            couleur text NOT NULL UNIQUE,
            description text,
            publie boolean NOT NULL DEFAULT true,
            ordre integer NOT NULL DEFAULT 0,
            cree_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("ALTER TABLE evenement ADD COLUMN IF NOT EXISTS type_evenement_id uuid REFERENCES type_evenement(id) ON DELETE SET NULL")
    op.execute("CREATE INDEX IF NOT EXISTS idx_evenement_type_evenement ON evenement(type_evenement_id)")

    bind = op.get_bind()
    insert = sa.text(
        "INSERT INTO type_evenement (code, nom, couleur, description, publie, ordre) "
        "VALUES (:code, :nom, :couleur, :description, true, :ordre) "
        "ON CONFLICT (code) DO NOTHING"
    )
    for ordre, (code, nom, couleur, description) in enumerate(_SEED):
        bind.execute(insert, {"code": code, "nom": nom, "couleur": couleur, "description": description, "ordre": ordre})


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_evenement_type_evenement")
    op.execute("ALTER TABLE evenement DROP COLUMN IF EXISTS type_evenement_id")
    op.execute("DROP TABLE IF EXISTS type_evenement")
