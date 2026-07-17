# ruff: noqa: E501 - migrations carry long SQL lines
"""Mandatory 'Instructions du canal' column on every board.

Each board receives, in first position, a dedicated column where channel
instructions land as cards. A flag marks the column so it is recognisable and the
workflow can target it. A back-office parameter (collab_colonne_instructions_auto,
default true) governs whether new boards get it. Existing boards are backfilled:
every board without an instruction column gets one prepended.

Revision ID: 0122_colonne_instructions
Revises: 0121_canal_workflow
Create Date: 2026-07-11
"""
from __future__ import annotations

from alembic import op

revision = "0122_colonne_instructions"
down_revision = "0121_canal_workflow"
branch_labels = None
depends_on = None

_NOM = "Instructions du canal"


def upgrade() -> None:
    op.execute("ALTER TABLE collab_colonne ADD COLUMN IF NOT EXISTS instructions boolean NOT NULL DEFAULT false")
    op.execute(
        """
        INSERT INTO parametre (cle, valeur, categorie, description)
        VALUES ('collab_colonne_instructions_auto', 'true'::jsonb, 'collaboration',
                'Ajoute automatiquement une colonne Instructions du canal en premiere position de chaque nouveau tableau.')
        ON CONFLICT (cle) DO NOTHING
        """
    )
    # Backfill: every existing board without an instruction column gets one at
    # position 0 (existing columns shift by one). Idempotent via the flag check.
    op.execute(
        f"""
        DO $$
        DECLARE t record;
        BEGIN
          FOR t IN SELECT id FROM collab_tableau LOOP
            IF NOT EXISTS (SELECT 1 FROM collab_colonne WHERE tableau_id = t.id AND instructions = true) THEN
              UPDATE collab_colonne SET position = position + 1 WHERE tableau_id = t.id;
              INSERT INTO collab_colonne (tableau_id, nom, position, instructions)
              VALUES (t.id, '{_NOM}', 0, true);
            END IF;
          END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM collab_colonne WHERE instructions = true")
    op.execute("ALTER TABLE collab_colonne DROP COLUMN IF EXISTS instructions")
    op.execute("DELETE FROM parametre WHERE cle = 'collab_colonne_instructions_auto'")
