# ruff: noqa: E501 - migrations carry long SQL lines
"""Technical (support) super-admin: a stable, server-side global-access authorization.

A technical/applicative super-admin (a support identity, NOT a business member) must
have total, cross-application access, including every Collaboration workspace, board and
canal it created, WITHOUT any membership. This is distinct from a member super-admin
(a person granted high governance) who only ever sees content they explicitly belong to.

The authorization is a stable column, ``utilisateur.acces_technique_global``, never a
hardcoded e-mail in the application code. The e-mail is used here ONLY to identify the
existing principal technical account during this one-off migration; from then on the
column is the single source of truth, editable from the back-office.

Revision ID: 0129_technical_super_admin
Revises: 0128_type_membre_nullable
Create Date: 2026-07-12
"""
from __future__ import annotations

from alembic import op

revision = "0129_technical_super_admin"
down_revision = "0128_type_membre_nullable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE utilisateur ADD COLUMN IF NOT EXISTS acces_technique_global boolean NOT NULL DEFAULT false")
    # Grant total technical access to the existing technical super-admin support account(s):
    # applicative accounts with the super_admin role and no member record (membre_id IS NULL),
    # i.e. the principal support identity (saintgabrielsacerdoceroyal@gmail.com). Member
    # super-admins keep membership-only content access.
    # Exclude demonstration accounts (@exemple.com): a technical role must never be
    # granted to a demo or non-validated production account.
    op.execute(
        "UPDATE utilisateur SET acces_technique_global = true "
        "WHERE role = 'super_admin' AND membre_id IS NULL AND email NOT LIKE '%%@exemple.com'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE utilisateur DROP COLUMN IF EXISTS acces_technique_global")
