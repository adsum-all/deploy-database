# ruff: noqa: E501 - migrations carry long SQL lines
"""Membership state and an admin-only confidential note, distinct from identity.

The consecration title (Berger/Bergere) and its name already live on membre
(est_berger, nom_pastoral, added in 0057) and are kept strictly separate from the
honorific function (fonction_cle). This migration adds what governance still
lacked so the administration can manage the full life cycle:

- appartenance: the member's relationship state with the fraternity (actif,
  parti, retire, suspendu, archive), distinct from the account status (statut).
- note_confidentielle: an OPTIONAL admin-only internal note (reason for a
  departure, a title withdrawal, a suspension...). It is never exposed to the
  member; only a dedicated admin endpoint returns it.
- berger_depuis: optional date the consecration title was granted (light history;
  every change is also traced in the audit log).

Columns are only added, never dropped or renamed.

Revision ID: 0058_consecration_confidentiel
Revises: 0057_identite_civile
Create Date: 2026-07-04
"""
from __future__ import annotations

from alembic import op

revision = "0058_consecration_confidentiel"
down_revision = "0057_identite_civile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS appartenance text NOT NULL DEFAULT 'actif'")
    op.execute("ALTER TABLE membre DROP CONSTRAINT IF EXISTS membre_appartenance_chk")
    op.execute(
        "ALTER TABLE membre ADD CONSTRAINT membre_appartenance_chk "
        "CHECK (appartenance IN ('actif', 'parti', 'retire', 'suspendu', 'archive')) NOT VALID"
    )
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS note_confidentielle text")
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS berger_depuis date")


def downgrade() -> None:
    op.execute("ALTER TABLE membre DROP CONSTRAINT IF EXISTS membre_appartenance_chk")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS berger_depuis")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS note_confidentielle")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS appartenance")
