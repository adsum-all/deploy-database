# ruff: noqa: E501 - migrations carry long SQL lines
"""Make custom board templates global instead of workspace-scoped.

A custom board template is no longer tied to a workspace: once created it is a
library asset available to every workspace and every collaborator, exactly like
the built-in catalogue. Two changes:

- ``espace_id`` becomes nullable and its FK switches to ON DELETE SET NULL, so a
  template survives the deletion of the workspace it happened to be created from
  (it now records at most an optional origin, never an ownership binding).
- ``visibilite`` is reframed from workspace scope to library scope: ``partage``
  (visible to everyone) replaces the old ``espace`` value, ``prive`` stays as
  "visible to the author only". The default becomes ``partage``.

Revision ID: 0163_collab_modele_perso_global
Revises: 0162_collab_modele_perso
Create Date: 2026-07-19
"""
from __future__ import annotations

from alembic import op

revision = "0163_collab_modele_perso_global"
down_revision = "0162_collab_modele_perso"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE collab_modele_perso ALTER COLUMN espace_id DROP NOT NULL")
    op.execute("ALTER TABLE collab_modele_perso DROP CONSTRAINT IF EXISTS collab_modele_perso_espace_id_fkey")
    op.execute(
        "ALTER TABLE collab_modele_perso ADD CONSTRAINT collab_modele_perso_espace_id_fkey "
        "FOREIGN KEY (espace_id) REFERENCES collab_espace(id) ON DELETE SET NULL"
    )
    # Reframe visibility: workspace scope -> library scope.
    op.execute("ALTER TABLE collab_modele_perso DROP CONSTRAINT IF EXISTS collab_modele_perso_visibilite_chk")
    op.execute("UPDATE collab_modele_perso SET visibilite = 'partage' WHERE visibilite = 'espace'")
    op.execute("ALTER TABLE collab_modele_perso ALTER COLUMN visibilite SET DEFAULT 'partage'")
    op.execute("ALTER TABLE collab_modele_perso ADD CONSTRAINT collab_modele_perso_visibilite_chk CHECK (visibilite IN ('partage', 'prive'))")


def downgrade() -> None:
    op.execute("ALTER TABLE collab_modele_perso DROP CONSTRAINT IF EXISTS collab_modele_perso_visibilite_chk")
    op.execute("UPDATE collab_modele_perso SET visibilite = 'espace' WHERE visibilite = 'partage'")
    op.execute("ALTER TABLE collab_modele_perso ALTER COLUMN visibilite SET DEFAULT 'espace'")
    op.execute("ALTER TABLE collab_modele_perso ADD CONSTRAINT collab_modele_perso_visibilite_chk CHECK (visibilite IN ('espace', 'prive'))")
    op.execute("DELETE FROM collab_modele_perso WHERE espace_id IS NULL")
    op.execute("ALTER TABLE collab_modele_perso DROP CONSTRAINT IF EXISTS collab_modele_perso_espace_id_fkey")
    op.execute(
        "ALTER TABLE collab_modele_perso ADD CONSTRAINT collab_modele_perso_espace_id_fkey "
        "FOREIGN KEY (espace_id) REFERENCES collab_espace(id) ON DELETE CASCADE"
    )
    op.execute("ALTER TABLE collab_modele_perso ALTER COLUMN espace_id SET NOT NULL")
