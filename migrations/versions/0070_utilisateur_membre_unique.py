# ruff: noqa: E501 - migrations carry long SQL lines
"""One login account per member: UNIQUE(membre_id) on utilisateur.

Defense-in-depth for the access-group model: a member must map to at most one
login account, so granting platform access can never silently re-point an
existing account to another member (audit attribution stays truthful). Email-only
service accounts keep ``membre_id NULL``; PostgreSQL allows many NULLs under a
UNIQUE constraint, so they are unaffected. The constraint is added only when the
current data has no duplicate, so the migration never fails on existing data; the
application-level guard already prevents new duplicates.

Revision ID: 0070_utilisateur_membre_uq
Revises: 0069_emargement_externe
Create Date: 2026-07-05
"""
from __future__ import annotations

from alembic import op

revision = "0070_utilisateur_membre_uq"
down_revision = "0069_emargement_externe"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'utilisateur_membre_uniq') THEN
                IF NOT EXISTS (
                    SELECT membre_id FROM utilisateur
                    WHERE membre_id IS NOT NULL
                    GROUP BY membre_id HAVING count(*) > 1
                ) THEN
                    ALTER TABLE utilisateur ADD CONSTRAINT utilisateur_membre_uniq UNIQUE (membre_id);
                END IF;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE utilisateur DROP CONSTRAINT IF EXISTS utilisateur_membre_uniq")
