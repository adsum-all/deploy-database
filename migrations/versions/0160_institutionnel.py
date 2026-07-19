# ruff: noqa: E501 - migrations carry long SQL lines
"""Institutional identity and dates, configurable per organisation (no hardcoding).

- Organisation identity lives in ``integration_config`` (key/value, admin-editable):
  name, short name, official site, founding/anniversary date, patron saint and its
  feast date, reference timezone, institutional signature. Seeded with the current
  values so nothing changes today, but they are data, editable, and reusable by any
  other association deploying ADSUM.
- ``date_institutionnelle``: a configurable list of institutional dates (fraternity
  anniversary, patron feast, commemorations...) with an optional reminder and
  visibility, each able to drive an automatic Information later.

Revision ID: 0160_institutionnel
Revises: 0159_information_canaux
Create Date: 2026-07-19
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0160_institutionnel"
down_revision = "0159_information_canaux"
branch_labels = None
depends_on = None

_IDENTITE_DEFAUTS = [
    ("org_nom", "Sacerdoce Royal"),
    ("org_nom_court", "ADSUM"),
    ("org_site", "https://sacerdoceroyal.info"),
    ("org_fondation_date", ""),
    ("org_saint_patron", "Saint Gabriel"),
    ("org_saint_patron_date", ""),
    ("org_fuseau", "Africa/Abidjan"),
    ("org_signature", "Fraternite du Sacerdoce Royal"),
    ("org_contact", ""),
]


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS date_institutionnelle (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            nom text NOT NULL,
            description text,
            type text NOT NULL DEFAULT 'commemoration',
            date_fixe date,
            mois integer,
            jour integer,
            rappel_jours integer NOT NULL DEFAULT 7,
            visibilite text NOT NULL DEFAULT 'membre',
            actif boolean NOT NULL DEFAULT true,
            cree_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("ALTER TABLE date_institutionnelle ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY date_institutionnelle_select ON date_institutionnelle FOR SELECT "
        "USING (adsum_current_role() = ANY(ARRAY['super_admin','admin','gestionnaire','direction','controleur','membre']::text[]))"
    )
    op.execute(
        "CREATE POLICY date_institutionnelle_write ON date_institutionnelle FOR ALL "
        "USING (adsum_current_role() = ANY(ARRAY['super_admin','admin']::text[])) "
        "WITH CHECK (adsum_current_role() = ANY(ARRAY['super_admin','admin']::text[]))"
    )

    bind = op.get_bind()
    for cle, valeur in _IDENTITE_DEFAUTS:
        bind.execute(
            sa.text("INSERT INTO integration_config (cle, valeur) VALUES (:cle, :valeur) ON CONFLICT (cle) DO NOTHING"),
            {"cle": cle, "valeur": valeur},
        )


def downgrade() -> None:
    op.execute("DELETE FROM integration_config WHERE cle LIKE 'org_%'")
    op.execute("DROP TABLE IF EXISTS date_institutionnelle")
