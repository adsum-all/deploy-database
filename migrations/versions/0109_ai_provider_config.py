"""AI provider configuration, managed from the back office.

The moderator channel transcribes voice notes (speech to text) and drafts a
professional redaction (LLM). Providers must be swappable in one click without a
redeploy, so their configuration lives in the database, not in code or env vars.
Because a provider row holds an API key, this is a secrets table and is hardened
accordingly: the key is stored Fernet-encrypted (never in clear), row level
security is enabled with no policy (deny all through PostgREST) and anon /
authenticated are revoked. The API reaches it only through the owner connection.

At most one provider per capability (stt / llm) is active at a time, enforced by a
partial unique index.

Revision ID: 0109_ai_provider_config
Revises: 0108_item_assigne_fk
"""
from __future__ import annotations

from alembic import op

revision = "0109_ai_provider_config"
down_revision = "0108_item_assigne_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_provider_config (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            capacite text NOT NULL CHECK (capacite IN ('stt', 'llm')),
            fournisseur text NOT NULL,
            libelle text NOT NULL,
            modele text NOT NULL,
            endpoint text,
            cle_chiffree bytea,
            params jsonb NOT NULL DEFAULT '{}'::jsonb,
            actif boolean NOT NULL DEFAULT false,
            gratuit boolean NOT NULL DEFAULT false,
            ordre integer NOT NULL DEFAULT 0,
            cree_le timestamptz NOT NULL DEFAULT now(),
            maj_le timestamptz NOT NULL DEFAULT now(),
            cree_par uuid REFERENCES utilisateur(id) ON DELETE SET NULL
        )
        """
    )
    # At most one active provider per capability.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_ai_provider_actif "
        "ON ai_provider_config (capacite) WHERE actif"
    )
    # Secrets-table hardening: deny all through PostgREST (no policy) and revoke the
    # Supabase client roles. The API connects as the table owner and bypasses RLS.
    op.execute("ALTER TABLE ai_provider_config ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON ai_provider_config FROM anon, authenticated")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ai_provider_config")
