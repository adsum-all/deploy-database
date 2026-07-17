# ruff: noqa: E501 - migrations carry long SQL lines
"""Register the mobile member application in the access catalogue.

``adsum-mobile`` is the Capacitor Android/iOS shell wrapping the member web application.
It is a real, existing member-facing application, so every member sees it by default in
« Mes applications » (est_defaut = true), exactly like the member web space. The public
site (``adsum-public``) is intentionally NOT registered: it has no login and no access to
grant or revoke, so it does not belong to the access governance.

Revision ID: 0137_app_mobile_membre
Revises: 0136_app_acces_cascade_defaut
Create Date: 2026-07-13
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0137_app_mobile_membre"
down_revision = "0136_app_acces_cascade_defaut"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "INSERT INTO application (code, nom, description, url, actif, ordre, est_defaut) "
            "VALUES (:code, :nom, :descr, :url, true, :ordre, true) "
            "ON CONFLICT (code) DO UPDATE SET est_defaut = true, nom = EXCLUDED.nom, description = EXCLUDED.description, url = EXCLUDED.url"
        ),
        {
            "code": "mobile",
            "nom": "ADSUM Mobile",
            "descr": "L'application mobile de votre espace membre (Android et iOS) : carte, QR, calendrier et demandes, dans votre poche.",
            "url": "https://adsum-web-membre.pages.dev",
            "ordre": 0,
        },
    )


def downgrade() -> None:
    op.execute("DELETE FROM application WHERE code = 'mobile'")
