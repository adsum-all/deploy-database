# ruff: noqa: E501 - migrations carry long SQL lines
"""The mobile app is the Android build of the member space, not a separate application.

Showing ``mobile`` as its own card in « Mes applications » (and as a distinct governance
entry) is a confusing duplicate: it is the SAME member application, only the Android
version. We deactivate the access-catalogue entry so members see the member space exactly
once. The Android build remains a packaging/repository concern (handled in the applications
repository organisation), not a distinct access-governance application.

Revision ID: 0139_app_mobile_non_doublon
Revises: 0138_membre_groupe_acces_requis
Create Date: 2026-07-13
"""
from __future__ import annotations

from alembic import op

revision = "0139_app_mobile_non_doublon"
down_revision = "0138_membre_groupe_acces_requis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE application SET actif = false, est_defaut = false WHERE code = 'mobile'")


def downgrade() -> None:
    op.execute("UPDATE application SET actif = true, est_defaut = true WHERE code = 'mobile'")
