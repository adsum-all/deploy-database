"""Readable, versioned, admin-editable consent documents.

The member must be able to open and read each required document (data protection,
confidentiality charter, engagement letter, internal rules) before accepting it.
Documents are bilingual (FR/EN), versioned (a new version supersedes the active
one, older versions are kept for the signature evidence trail) and editable by
the administration.

Revision ID: 0032_consent_docs
Revises: 0031_correction
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0032_consent_docs"
down_revision = "0031_correction"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS document_consentement (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            cle text NOT NULL,
            version integer NOT NULL DEFAULT 1,
            titre text NOT NULL,
            titre_en text,
            contenu text NOT NULL,
            contenu_en text,
            bloquant boolean NOT NULL DEFAULT true,
            ordre integer NOT NULL DEFAULT 100,
            actif boolean NOT NULL DEFAULT true,
            publie_le timestamptz NOT NULL DEFAULT now(),
            publie_par uuid,
            CONSTRAINT document_consentement_cle_version_uq UNIQUE (cle, version)
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_consent_active ON document_consentement (cle) WHERE actif")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS document_consentement")
