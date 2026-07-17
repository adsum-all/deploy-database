# ruff: noqa: E501 - migrations carry long SQL lines
"""Two-step access strictly linked: revoking visibility cascades to the app's rights.

- ``membre_groupe.application_code`` ties a group assignment to an application, so
  revoking a member's access to that application removes every group it granted, in one
  action (rights can never outlive the visibility that justified them). Global group
  assignments (from « Acces & groupes ») keep application_code NULL and are untouched.
- ``application.est_defaut`` marks applications every member sees by default in « Mes
  applications » without any grant: the member app itself.

Revision ID: 0136_app_acces_cascade_defaut
Revises: 0135_application_roles
Create Date: 2026-07-13
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0136_app_acces_cascade_defaut"
down_revision = "0135_application_roles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE membre_groupe ADD COLUMN IF NOT EXISTS application_code text REFERENCES application(code) ON DELETE SET NULL")
    op.execute("CREATE INDEX IF NOT EXISTS idx_mg_application ON membre_groupe(application_code)")
    op.execute("ALTER TABLE application ADD COLUMN IF NOT EXISTS est_defaut boolean NOT NULL DEFAULT false")
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "INSERT INTO application (code, nom, description, url, actif, ordre, est_defaut) "
            "VALUES (:code, :nom, :descr, :url, true, :ordre, true) "
            "ON CONFLICT (code) DO UPDATE SET est_defaut = true, nom = EXCLUDED.nom, description = EXCLUDED.description, url = EXCLUDED.url"
        ),
        {
            "code": "web-membre",
            "nom": "ADSUM Espace Membre",
            "descr": "Votre espace personnel : carte, calendrier, activites, profil et demandes.",
            "url": "https://adsum-web-membre.pages.dev",
            "ordre": -1,
        },
    )


def downgrade() -> None:
    op.execute("DELETE FROM application WHERE code = 'web-membre'")
    op.execute("ALTER TABLE application DROP COLUMN IF EXISTS est_defaut")
    op.execute("DROP INDEX IF EXISTS idx_mg_application")
    op.execute("ALTER TABLE membre_groupe DROP COLUMN IF EXISTS application_code")
