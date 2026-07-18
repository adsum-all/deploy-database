# ruff: noqa: E501 - migrations carry long SQL lines
"""Neural text-to-speech: audio cache table and TTS provider rows.

Adds ``tts_cache`` (one synthesised audio per hash of provider+voice+language+
cleaned text, so a frequently listened content is synthesised once) and seeds the
``tts`` capability into the existing AI-provider referential (``ai_provider_config``),
inactive until an administrator pastes a key in Reglages IA. Providers seeded:
OpenAI (excellent French voices), ElevenLabs (top naturalness) and Cloudflare
Workers AI (MeloTTS, French). The device's native voice remains the always-on
fallback in the member app.

Revision ID: 0155_tts_cache
Revises: 0154_informations
Create Date: 2026-07-18
"""
from __future__ import annotations

from alembic import op

revision = "0155_tts_cache"
down_revision = "0154_informations"
branch_labels = None
depends_on = None

_LECTURE = "ARRAY['super_admin', 'admin', 'gestionnaire', 'direction', 'membre', 'controleur']::text[]"
_ECRITURE = "ARRAY['super_admin', 'admin', 'gestionnaire']::text[]"

_PROVIDERS = (
    ("openai", "OpenAI TTS (voix naturelles fr/en)", "gpt-4o-mini-tts", 10),
    ("elevenlabs", "ElevenLabs (voix ultra naturelles)", "eleven_multilingual_v2", 20),
    ("cloudflare", "Cloudflare Workers AI (MeloTTS)", "@cf/myshell-ai/melotts", 30),
)


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tts_cache (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            cle_hash text UNIQUE NOT NULL,
            mime text NOT NULL DEFAULT 'audio/mpeg',
            audio bytea NOT NULL,
            cree_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("ALTER TABLE tts_cache ENABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tts_cache_select ON tts_cache")
    op.execute(f"CREATE POLICY tts_cache_select ON tts_cache FOR SELECT USING (adsum_current_role() = ANY({_LECTURE}))")
    op.execute("DROP POLICY IF EXISTS tts_cache_write ON tts_cache")
    op.execute(f"CREATE POLICY tts_cache_write ON tts_cache FOR ALL USING (adsum_current_role() = ANY({_ECRITURE})) WITH CHECK (adsum_current_role() = ANY({_ECRITURE}))")

    # Widen the capability CHECK so 'tts' joins 'stt' and 'llm'.
    op.execute("ALTER TABLE ai_provider_config DROP CONSTRAINT IF EXISTS ai_provider_config_capacite_check")
    op.execute("ALTER TABLE ai_provider_config ADD CONSTRAINT ai_provider_config_capacite_check CHECK (capacite = ANY (ARRAY['stt'::text, 'llm'::text, 'tts'::text]))")

    for fournisseur, libelle, modele, ordre in _PROVIDERS:
        op.execute(
            "INSERT INTO ai_provider_config (capacite, fournisseur, libelle, modele, actif, gratuit, ordre) "
            f"SELECT 'tts', '{fournisseur}', '{libelle}', '{modele}', false, false, {ordre} "
            f"WHERE NOT EXISTS (SELECT 1 FROM ai_provider_config WHERE capacite = 'tts' AND fournisseur = '{fournisseur}')"
        )


def downgrade() -> None:
    op.execute("DELETE FROM ai_provider_config WHERE capacite = 'tts'")
    op.execute("ALTER TABLE ai_provider_config DROP CONSTRAINT IF EXISTS ai_provider_config_capacite_check")
    op.execute("ALTER TABLE ai_provider_config ADD CONSTRAINT ai_provider_config_capacite_check CHECK (capacite = ANY (ARRAY['stt'::text, 'llm'::text]))")
    op.execute("DROP POLICY IF EXISTS tts_cache_write ON tts_cache")
    op.execute("DROP POLICY IF EXISTS tts_cache_select ON tts_cache")
    op.execute("DROP TABLE IF EXISTS tts_cache")
