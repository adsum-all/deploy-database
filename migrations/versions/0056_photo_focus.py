# ruff: noqa: E501 - migrations carry long SQL lines
"""Per-photo focal point for face-centred display (no distortion).

The identity photo is shown in round avatars (profile, member file) and portrait
cards (QR). To keep the face perfectly framed without ever distorting the image,
each photo carries a focal point in percentages (0-100): the display uses it as
CSS object-position with object-fit: cover. It is display-only metadata, so a
member can adjust the framing of an already-validated photo without any new
validation. A replacement photo stages its own focal point, promoted with the
photo when the administration validates.

NULL means "not set": the display falls back to the safe upper-centre default
(50 / 30) that suits head-and-shoulders identity photos.

Revision ID: 0056_photo_focus
Revises: 0055_rls_compteurs
Create Date: 2026-07-04
"""
from __future__ import annotations

from alembic import op

revision = "0056_photo_focus"
down_revision = "0055_rls_compteurs"
branch_labels = None
depends_on = None

_COLUMNS = ("photo_focus_x", "photo_focus_y", "photo_pending_focus_x", "photo_pending_focus_y")


def upgrade() -> None:
    for col in _COLUMNS:
        op.execute(f"ALTER TABLE membre ADD COLUMN IF NOT EXISTS {col} smallint")
        op.execute(f"ALTER TABLE membre DROP CONSTRAINT IF EXISTS chk_{col}_range")
        op.execute(f"ALTER TABLE membre ADD CONSTRAINT chk_{col}_range CHECK ({col} IS NULL OR ({col} >= 0 AND {col} <= 100)) NOT VALID")


def downgrade() -> None:
    for col in _COLUMNS:
        op.execute(f"ALTER TABLE membre DROP CONSTRAINT IF EXISTS chk_{col}_range")
        op.execute(f"ALTER TABLE membre DROP COLUMN IF EXISTS {col}")
