"""Foreign keys on the collaboration actor columns.

Several collaboration tables store the acting login account as a bare uuid with no
referential integrity: collab_tableau.cree_par, collab_carte.cree_par,
collab_commentaire.auteur_id, collab_version.auteur_id (0009), collab_espace.
cree_par (0097), collab_piece.cree_par and collab_activite.auteur_id (0098). This
revision adds a foreign key to ``utilisateur(id)`` with ON DELETE SET NULL on each,
so an actor can never be an orphan id and a deleted account nulls the reference
instead of dangling. Defensive: any pre-existing value that does not match a live
account is set to NULL first so the constraint applies cleanly.

Revision ID: 0099_collab_actor_fks
Revises: 0098_collab_social
"""
from __future__ import annotations

from alembic import op

revision = "0099_collab_actor_fks"
down_revision = "0098_collab_social"
branch_labels = None
depends_on = None

# (table, column, target constraint name, other constraint names to drop first).
# Some actor FKs already exist in prod under an older name (added by an earlier
# migration); this revision is idempotent: it drops any known variant on the
# column, then adds the canonical constraint with ON DELETE SET NULL.
ACTOR_FKS = (
    ("collab_tableau", "cree_par", "fk_collab_tableau_cree_par", ()),
    ("collab_carte", "cree_par", "fk_collab_carte_cree_par", ()),
    ("collab_commentaire", "auteur_id", "fk_collab_commentaire_auteur", ("fk_collab_commentaire_auteur_id",)),
    ("collab_version", "auteur_id", "fk_collab_version_auteur", ("fk_collab_version_auteur_id",)),
    ("collab_espace", "cree_par", "fk_collab_espace_cree_par", ()),
    ("collab_piece", "cree_par", "fk_collab_piece_cree_par", ()),
    ("collab_activite", "auteur_id", "fk_collab_activite_auteur", ()),
)


def upgrade() -> None:
    for table, column, constraint, autres in ACTOR_FKS:
        for name in (constraint, *autres):
            op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}")
        op.execute(
            f"UPDATE {table} SET {column} = NULL "
            f"WHERE {column} IS NOT NULL AND {column} NOT IN (SELECT id FROM utilisateur)"
        )
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT {constraint} "
            f"FOREIGN KEY ({column}) REFERENCES utilisateur(id) ON DELETE SET NULL"
        )


def downgrade() -> None:
    for table, _column, constraint, _autres in ACTOR_FKS:
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {constraint}")
