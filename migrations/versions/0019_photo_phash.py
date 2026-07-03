"""Perceptual hash of the member photo for the duplicate-detection photo signal.

A 64-bit difference hash (dHash) is computed on the client when the member
uploads their photo and stored here as a 16-character hex string. The duplicate
scan compares two members' hashes by Hamming distance, which needs no image
library on the server. Open-source and lightweight.

Revision ID: 0019_photo_phash
Revises: 0018_detection_doublon
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0019_photo_phash"
down_revision = "0018_detection_doublon"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS photo_phash text")


def downgrade() -> None:
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS photo_phash")
