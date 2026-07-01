"""Duplicate / fraud detection log and its configurable threshold.

The administration runs a multi-field similarity scan across members (name, date
of birth, phone, city, address, and photo when available). Each flagged pair is
stored here with its score and the per-signal breakdown, and can be confirmed or
dismissed. The decision threshold is stored in the parametre table so it can be
tuned without a deployment.

Revision ID: 0018_detection_doublon
Revises: 0017_demande_en_validation
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0018_detection_doublon"
down_revision = "0017_demande_en_validation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS detection_doublon (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            membre_a uuid NOT NULL REFERENCES membre(id) ON DELETE CASCADE,
            membre_b uuid NOT NULL REFERENCES membre(id) ON DELETE CASCADE,
            score numeric(4, 3) NOT NULL,
            signaux jsonb NOT NULL DEFAULT '{}'::jsonb,
            statut text NOT NULL DEFAULT 'nouveau'
                CHECK (statut IN ('nouveau', 'confirme', 'ignore')),
            detecte_le timestamptz NOT NULL DEFAULT now(),
            decide_le timestamptz,
            decide_par uuid,
            CONSTRAINT detection_doublon_pair_uq UNIQUE (membre_a, membre_b),
            CONSTRAINT detection_doublon_order_chk CHECK (membre_a < membre_b)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_detection_doublon_statut ON detection_doublon (statut, score DESC)")
    op.execute(
        """
        INSERT INTO parametre (cle, valeur, categorie, description)
        VALUES (
            'seuil_doublon', '0.6'::jsonb, 'doublon',
            'Similarity score in [0,1] above which a member pair is flagged as a potential duplicate. Default 0.6.'
        )
        ON CONFLICT (cle) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS detection_doublon")
    op.execute("DELETE FROM parametre WHERE cle = 'seuil_doublon'")
