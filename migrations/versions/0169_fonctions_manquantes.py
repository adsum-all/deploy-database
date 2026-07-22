# ruff: noqa: E501 - migrations carry long SQL lines
"""Add the two catalog functions the real organisation chart uses but that were missing.

The published organisation document lists an "Assistant(e) du Fondateur" (in the
leadership team, directly supporting the founder) and a "Responsable des missions"
(under the general controller). Both are added to the ``fonction_honorifique`` catalog
as transversal roles (niveau_hierarchique NULL) so they enrich the chart without
altering the apex chain fondateur -> moderateur -> berger des missions -> controleur
general -> intendant general.

Revision ID: 0169_fonctions_manquantes
Revises: 0168_equipes_speciales
Create Date: 2026-07-22
"""
from __future__ import annotations

from alembic import op

revision = "0169_fonctions_manquantes"
down_revision = "0168_equipes_speciales"
branch_labels = None
depends_on = None

_NOUVELLES = ("assistant_fondateur", "responsable_missions")


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO fonction_honorifique (cle, libelle_h, libelle_f, libelle_n, est_vip, ordre, actif, famille, niveau, categorie, abreviation, niveau_hierarchique, transversal)
        VALUES
            ('assistant_fondateur', 'Assistant du Fondateur', 'Assistante du Fondateur', 'Assistant(e) du Fondateur', true, 25, true, 'direction', 15, 'fonction_speciale', NULL, NULL, true),
            ('responsable_missions', 'Responsable des missions', 'Responsable des missions', 'Responsable des missions', false, 95, true, 'responsables', 65, 'fonction', 'Resp. miss.', NULL, true)
        ON CONFLICT (cle) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM fonction_honorifique WHERE cle = ANY(ARRAY['assistant_fondateur', 'responsable_missions'])")
