# ruff: noqa: E501 - migrations carry long SQL lines
"""Per-account display preferences and per-application group tagging.

Two small, additive columns:

1. ``utilisateur.preferences`` (jsonb, default '{}'): personal display preferences of the
   signed-in account (e.g. the events view mode calendar/list). Server-side so the choice
   follows the account across browsers and devices, instead of living only in one
   browser's localStorage. Strictly validated by the API (known keys only), never any
   sensitive data.

2. ``groupe_acces.application_code`` (nullable, FK to application(code) like
   membre_groupe.application_code): lets an access group be tagged with the application it
   serves, so the governance UI can organise groups per application (tabs/filter) instead
   of one mixed list. Nullable: existing and cross-application groups stay valid untagged.

Revision ID: 0146_prefs_compte_groupe_app
Revises: 0145_tableau_favori_personnel
Create Date: 2026-07-17
"""
from __future__ import annotations

from alembic import op

revision = "0146_prefs_compte_groupe_app"
down_revision = "0145_tableau_favori_personnel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE utilisateur ADD COLUMN IF NOT EXISTS preferences jsonb NOT NULL DEFAULT '{}'::jsonb")
    op.execute("ALTER TABLE groupe_acces ADD COLUMN IF NOT EXISTS application_code text REFERENCES application(code) ON DELETE SET NULL")
    op.execute("CREATE INDEX IF NOT EXISTS idx_groupe_acces_application ON groupe_acces(application_code)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_groupe_acces_application")
    op.execute("ALTER TABLE groupe_acces DROP COLUMN IF EXISTS application_code")
    op.execute("ALTER TABLE utilisateur DROP COLUMN IF EXISTS preferences")
