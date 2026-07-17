# ruff: noqa: E501 - migrations carry long SQL lines
"""Authorized instruction emitters per workspace channel.

The instruction bot is not open to everyone. Each workspace channel authorizes a
bounded set of emitters (canal_emetteurs_max, default 1). A voice note routes to a
workspace only when its sender is an authorized emitter of that workspace; else it
falls back to the global channel. Reads for the committee roles, writes for the
committee (mirrors the collab_* convention of 0116).

Revision ID: 0125_canal_emetteurs
Revises: 0124_corbeille_suppression
Create Date: 2026-07-11
"""
from __future__ import annotations

from alembic import op

revision = "0125_canal_emetteurs"
down_revision = "0124_corbeille_suppression"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collab_espace_emetteur (
            espace_id uuid NOT NULL REFERENCES collab_espace(id) ON DELETE CASCADE,
            utilisateur_id uuid NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE,
            ajoute_par uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            ajoute_le timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (espace_id, utilisateur_id)
        )
        """
    )
    op.execute("ALTER TABLE collab_espace_emetteur ENABLE ROW LEVEL SECURITY")
    op.execute("CREATE POLICY collab_espace_emetteur_select ON collab_espace_emetteur FOR SELECT USING (adsum_current_role() = ANY(ARRAY['super_admin', 'admin', 'gestionnaire', 'direction']::text[]))")
    op.execute("CREATE POLICY collab_espace_emetteur_write ON collab_espace_emetteur FOR ALL USING (adsum_current_role() = ANY(ARRAY['super_admin', 'admin', 'gestionnaire']::text[])) WITH CHECK (adsum_current_role() = ANY(ARRAY['super_admin', 'admin', 'gestionnaire']::text[]))")
    op.execute(
        """
        INSERT INTO parametre (cle, valeur, categorie, description)
        VALUES ('canal_emetteurs_max', '1'::jsonb, 'collaboration',
                'Nombre maximum de personnes autorisees a emettre des instructions via le bot pour un espace canal (defaut 1).')
        ON CONFLICT (cle) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS collab_espace_emetteur")
    op.execute("DELETE FROM parametre WHERE cle = 'canal_emetteurs_max'")
