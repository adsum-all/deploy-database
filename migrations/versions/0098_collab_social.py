"""Collaboration social layer: attachments, reactions, activity feed, mentions,
read receipts and collaboration notifications, plus the last card fields.

Completes the port of the Lovable prototype data model. Every collaborator is a
login account (``utilisateur``), consistent with 0097. Additive only: existing
collaboration tables, data and the other applications are untouched.

Revision ID: 0098_collab_social
Revises: 0097_collab_espaces
"""
from __future__ import annotations

from alembic import op

revision = "0098_collab_social"
down_revision = "0097_collab_espaces"
branch_labels = None
depends_on = None

COMITE = "ARRAY['super_admin', 'admin', 'gestionnaire']::text[]"
LECTURE = "ARRAY['super_admin', 'admin', 'gestionnaire', 'direction']::text[]"

NEW_TABLES = (
    "collab_piece",
    "collab_reaction",
    "collab_activite",
    "collab_commentaire_mention",
    "collab_commentaire_lu",
    "collab_notification",
)


def upgrade() -> None:
    # 1) Attachments: on a card or on a comment (exactly one of the two).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collab_piece (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            carte_id uuid REFERENCES collab_carte(id) ON DELETE CASCADE,
            commentaire_id uuid REFERENCES collab_commentaire(id) ON DELETE CASCADE,
            nom text NOT NULL,
            taille bigint NOT NULL DEFAULT 0,
            type text NOT NULL DEFAULT '',
            url text,
            couverture boolean NOT NULL DEFAULT false,
            cree_par uuid,
            cree_le timestamptz DEFAULT now(),
            CONSTRAINT collab_piece_cible CHECK (
                (carte_id IS NOT NULL)::int + (commentaire_id IS NOT NULL)::int = 1
            )
        )
        """
    )

    # 2) Reactions on a comment (thumbs up / check), one per account and type.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collab_reaction (
            commentaire_id uuid NOT NULL REFERENCES collab_commentaire(id) ON DELETE CASCADE,
            utilisateur_id uuid NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE,
            type text NOT NULL,
            cree_le timestamptz DEFAULT now(),
            PRIMARY KEY (commentaire_id, utilisateur_id, type)
        )
        """
    )

    # 3) Card activity feed (created, moved, commented, ...).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collab_activite (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            carte_id uuid NOT NULL REFERENCES collab_carte(id) ON DELETE CASCADE,
            auteur_id uuid,
            texte text NOT NULL,
            cree_le timestamptz DEFAULT now()
        )
        """
    )

    # 4) Comment mentions (who is @-mentioned): drives mention notifications.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collab_commentaire_mention (
            commentaire_id uuid NOT NULL REFERENCES collab_commentaire(id) ON DELETE CASCADE,
            utilisateur_id uuid NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE,
            PRIMARY KEY (commentaire_id, utilisateur_id)
        )
        """
    )

    # 5) Comment read receipts (who has read a comment).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collab_commentaire_lu (
            commentaire_id uuid NOT NULL REFERENCES collab_commentaire(id) ON DELETE CASCADE,
            utilisateur_id uuid NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE,
            lu_le timestamptz DEFAULT now(),
            PRIMARY KEY (commentaire_id, utilisateur_id)
        )
        """
    )

    # 6) Collaboration notifications (mention / assignation / echeance / suivie /
    #    demande d'acces), delivered to a login account. Kept separate from the
    #    global ``notification`` table so the two domains do not collide.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collab_notification (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            utilisateur_id uuid NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE,
            type text NOT NULL,
            carte_id uuid REFERENCES collab_carte(id) ON DELETE CASCADE,
            espace_id uuid REFERENCES collab_espace(id) ON DELETE CASCADE,
            texte text NOT NULL,
            lue boolean NOT NULL DEFAULT false,
            cree_le timestamptz DEFAULT now()
        )
        """
    )

    # 7) Remaining card fields from the prototype.
    op.execute("ALTER TABLE collab_carte ADD COLUMN IF NOT EXISTS echeance timestamptz")
    op.execute("ALTER TABLE collab_carte ADD COLUMN IF NOT EXISTS rappel text NOT NULL DEFAULT 'aucun'")
    op.execute("ALTER TABLE collab_carte ADD COLUMN IF NOT EXISTS modele boolean NOT NULL DEFAULT false")
    op.execute(
        "ALTER TABLE collab_carte ADD COLUMN IF NOT EXISTS couverture_id uuid "
        "REFERENCES collab_piece(id) ON DELETE SET NULL"
    )
    # A comment can be edited: keep the edit time.
    op.execute("ALTER TABLE collab_commentaire ADD COLUMN IF NOT EXISTS edite_le timestamptz")

    op.execute("CREATE INDEX IF NOT EXISTS idx_collab_piece_carte ON collab_piece(carte_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_collab_piece_commentaire ON collab_piece(commentaire_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_collab_reaction_commentaire ON collab_reaction(commentaire_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_collab_activite_carte ON collab_activite(carte_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_collab_notification_util ON collab_notification(utilisateur_id, lue)")

    for table in NEW_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_select ON {table} FOR SELECT "
            f"USING (adsum_current_role() = ANY({LECTURE}))"
        )
        op.execute(
            f"CREATE POLICY {table}_write ON {table} FOR ALL "
            f"USING (adsum_current_role() = ANY({COMITE})) "
            f"WITH CHECK (adsum_current_role() = ANY({COMITE}))"
        )


def downgrade() -> None:
    op.execute("ALTER TABLE collab_commentaire DROP COLUMN IF EXISTS edite_le")
    op.execute("ALTER TABLE collab_carte DROP COLUMN IF EXISTS couverture_id")
    op.execute("ALTER TABLE collab_carte DROP COLUMN IF EXISTS modele")
    op.execute("ALTER TABLE collab_carte DROP COLUMN IF EXISTS rappel")
    op.execute("ALTER TABLE collab_carte DROP COLUMN IF EXISTS echeance")
    for table in NEW_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_select ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_write ON {table}")
    op.execute("DROP TABLE IF EXISTS collab_notification CASCADE")
    op.execute("DROP TABLE IF EXISTS collab_commentaire_lu CASCADE")
    op.execute("DROP TABLE IF EXISTS collab_commentaire_mention CASCADE")
    op.execute("DROP TABLE IF EXISTS collab_activite CASCADE")
    op.execute("DROP TABLE IF EXISTS collab_reaction CASCADE")
    op.execute("DROP TABLE IF EXISTS collab_piece CASCADE")
