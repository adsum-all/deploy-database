"""Referential integrity for a note's audio piece.

0114 added collab_piece.canal_note_id as a bare uuid. This adds the foreign key so a
note's audio is cleaned up by the database when the note is deleted, instead of relying
solely on the application delete path (defence in depth: a direct delete or a future
code path can no longer leave a piece pointing at a vanished note).

Additive only. Revision ID: 0115_canal_piece_note_fk
Revises: 0114_canal_notes_et_liens
"""
from __future__ import annotations

from alembic import op

revision = "0115_canal_piece_note_fk"
down_revision = "0114_canal_notes_et_liens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Clear any dangling references first so the FK can be created cleanly.
    op.execute(
        "UPDATE collab_piece p SET canal_note_id = NULL "
        "WHERE canal_note_id IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM collab_canal_note n WHERE n.id = p.canal_note_id)"
    )
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'collab_piece_canal_note_fk') THEN "
        "ALTER TABLE collab_piece ADD CONSTRAINT collab_piece_canal_note_fk "
        "FOREIGN KEY (canal_note_id) REFERENCES collab_canal_note(id) ON DELETE CASCADE; "
        "END IF; END $$;"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE collab_piece DROP CONSTRAINT IF EXISTS collab_piece_canal_note_fk")
