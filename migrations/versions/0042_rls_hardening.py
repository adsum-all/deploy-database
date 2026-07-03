"""Enable Row Level Security on every public table and lock down PostgREST.

Supabase exposes an auto-generated REST/GraphQL API where the ``anon`` and
``authenticated`` roles hold broad grants on the public schema. Tables with RLS
disabled are therefore readable through that public API with the anon key,
bypassing the FastAPI. This migration:

- enables RLS on every public table that had it off (deny-by-default for any
  role that is not the table owner: with no policy, non-owner sees zero rows);
- revokes all anon/authenticated privileges on the public schema and its tables,
  since this stack never uses PostgREST (the API connects as the owner over the
  pooler and bypasses RLS, so the application is unaffected).

Reversible: downgrade re-grants anon/authenticated the standard privileges and
disables RLS on the tables listed here. The application role (owner) is never
affected in either direction.

Revision ID: 0042_rls_hardening
Revises: 0041_demande_ticket
Create Date: 2026-07-02
"""
from __future__ import annotations

from alembic import op

revision = "0042_rls_hardening"
down_revision = "0041_demande_ticket"
branch_labels = None
depends_on = None

# Tables that had RLS disabled (audited on the live database). The partitioned
# ``audit`` parent and its partitions are all included.
_TABLES = [
    "alembic_version", "attestation_manuelle",
    "audit", "audit_2026_01", "audit_2026_02", "audit_2026_03", "audit_2026_04",
    "audit_2026_05", "audit_2026_06", "audit_2026_07", "audit_2026_08",
    "audit_2026_09", "audit_2026_10", "audit_2026_11", "audit_2026_12", "audit_default",
    "auth_attempt", "code_consomme", "correction_historique", "detection_doublon",
    "document_consentement", "fonction_honorifique", "integration_config",
    "modele_message", "modification_membre", "notification_anniversaire",
    "notification_log", "participation", "pays_signature", "preference_notification",
    "question", "questionnaire", "reponse_questionnaire", "signature_engagement",
    "telegram_message", "type_notification",
]


def upgrade() -> None:
    for t in _TABLES:
        op.execute(f'ALTER TABLE IF EXISTS public."{t}" ENABLE ROW LEVEL SECURITY')
    # PostgREST lockdown: this stack does not use the auto-generated API.
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated")
    op.execute("REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated")
    op.execute("REVOKE ALL ON ALL FUNCTIONS IN SCHEMA public FROM anon, authenticated")
    op.execute("REVOKE USAGE ON SCHEMA public FROM anon, authenticated")
    # Do not hand these roles privileges on future objects either.
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated")
    op.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON FUNCTIONS FROM anon, authenticated")


def downgrade() -> None:
    op.execute("GRANT USAGE ON SCHEMA public TO anon, authenticated")
    op.execute("GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated")
    op.execute("GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated")
    for t in _TABLES:
        op.execute(f'ALTER TABLE IF EXISTS public."{t}" DISABLE ROW LEVEL SECURITY')
