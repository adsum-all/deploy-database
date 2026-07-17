"""Collaboration spaces, roles and board wiring, ported from the Lovable prototype.

Adds the space layer the prototype introduced: a ``collab_espace`` groups boards,
carries its own labels and a membership with a role (proprietaire / admin /
membre / observateur), plus access requests and private board participants. The
existing boards, columns and cards keep working: this revision is additive, and a
default "Comite" space adopts every existing board so nobody loses access.

The collaborator identity is the login account ``utilisateur`` (every committee
person signs in, and the backend already stores ``utilisateur.id`` as the actor
in ``cree_par`` / ``auteur_id``). Two tables created empty by 0096 referenced
``membre`` for assignees; they are rebuilt here against ``utilisateur`` for a
single, consistent identity. They hold no data yet, so the rebuild is safe.

Revision ID: 0097_collab_espaces
Revises: 0096_collab_carte_enrichie
"""
from __future__ import annotations

from alembic import op

revision = "0097_collab_espaces"
down_revision = "0096_collab_carte_enrichie"
branch_labels = None
depends_on = None

COMITE = "ARRAY['super_admin', 'admin', 'gestionnaire']::text[]"
LECTURE = "ARRAY['super_admin', 'admin', 'gestionnaire', 'direction']::text[]"

DEFAULT_TOKEN = "inv-comite-general"

NEW_TABLES = (
    "collab_espace",
    "collab_espace_membre",
    "collab_demande_acces",
    "collab_tableau_participant",
    "collab_carte_membre",
)
# collab_etiquette is intentionally NOT in NEW_TABLES: it was created with its RLS
# policies by 0096. This revision only alters its column (tableau_id -> espace_id);
# re-running its role policies here would raise 42710 (CREATE POLICY has no IF NOT
# EXISTS). Its 0096 policies are role-based and stay valid after the column swap.


def upgrade() -> None:
    # 1) Spaces: the collaboration unit. A committee works inside a space.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collab_espace (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            nom text NOT NULL,
            description text NOT NULL DEFAULT '',
            type text NOT NULL DEFAULT 'autre',
            couleur text NOT NULL DEFAULT '#2A4FAD',
            initiale text NOT NULL DEFAULT 'E',
            observateurs_commentent boolean NOT NULL DEFAULT true,
            archive boolean NOT NULL DEFAULT false,
            invitation_jeton text NOT NULL UNIQUE,
            cree_par uuid,
            cree_le timestamptz DEFAULT now(),
            maj_le timestamptz DEFAULT now()
        )
        """
    )

    # 2) Space membership: which login account collaborates, with which role.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collab_espace_membre (
            espace_id uuid NOT NULL REFERENCES collab_espace(id) ON DELETE CASCADE,
            utilisateur_id uuid NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE,
            role text NOT NULL DEFAULT 'membre',
            ajoute_le timestamptz DEFAULT now(),
            PRIMARY KEY (espace_id, utilisateur_id)
        )
        """
    )

    # 3) Access requests to join a space (one pending request per account).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collab_demande_acces (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            espace_id uuid NOT NULL REFERENCES collab_espace(id) ON DELETE CASCADE,
            utilisateur_id uuid NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE,
            cree_le timestamptz DEFAULT now(),
            UNIQUE (espace_id, utilisateur_id)
        )
        """
    )

    # 4) Participants of a private board (visibilite = 'prive').
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS collab_tableau_participant (
            tableau_id uuid NOT NULL REFERENCES collab_tableau(id) ON DELETE CASCADE,
            utilisateur_id uuid NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE,
            PRIMARY KEY (tableau_id, utilisateur_id)
        )
        """
    )

    # 5) Wire the existing board to a space and carry the prototype's board flags.
    op.execute(
        "ALTER TABLE collab_tableau ADD COLUMN IF NOT EXISTS espace_id uuid "
        "REFERENCES collab_espace(id) ON DELETE CASCADE"
    )
    op.execute("ALTER TABLE collab_tableau ADD COLUMN IF NOT EXISTS visibilite text NOT NULL DEFAULT 'espace'")
    op.execute("ALTER TABLE collab_tableau ADD COLUMN IF NOT EXISTS favori boolean NOT NULL DEFAULT false")
    op.execute("ALTER TABLE collab_tableau ADD COLUMN IF NOT EXISTS modele boolean NOT NULL DEFAULT false")

    # 6) Column styling from the prototype (color, collapsed, WIP limit, archived).
    op.execute("ALTER TABLE collab_colonne ADD COLUMN IF NOT EXISTS couleur text")
    op.execute("ALTER TABLE collab_colonne ADD COLUMN IF NOT EXISTS repliee boolean NOT NULL DEFAULT false")
    op.execute("ALTER TABLE collab_colonne ADD COLUMN IF NOT EXISTS wip integer")
    op.execute("ALTER TABLE collab_colonne ADD COLUMN IF NOT EXISTS archivee boolean NOT NULL DEFAULT false")

    # 7) Labels belong to the space (shared across its boards), not the board:
    #    move collab_etiquette from tableau_id to espace_id. The table was created
    #    empty by 0096 and is used by nothing yet, so the swap is lossless.
    op.execute("DROP INDEX IF EXISTS idx_collab_etiquette_tableau")
    op.execute("ALTER TABLE collab_etiquette DROP COLUMN IF EXISTS tableau_id")
    op.execute(
        "ALTER TABLE collab_etiquette ADD COLUMN espace_id uuid NOT NULL "
        "REFERENCES collab_espace(id) ON DELETE CASCADE"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_collab_etiquette_espace ON collab_etiquette(espace_id)")

    # 8) Assignees / followers on the login account, not the church member. The
    #    0096 table referenced membre; rebuild it against utilisateur (still empty).
    op.execute("DROP TABLE IF EXISTS collab_carte_membre CASCADE")
    op.execute(
        """
        CREATE TABLE collab_carte_membre (
            carte_id uuid NOT NULL REFERENCES collab_carte(id) ON DELETE CASCADE,
            utilisateur_id uuid NOT NULL REFERENCES utilisateur(id) ON DELETE CASCADE,
            role text NOT NULL DEFAULT 'assigne',
            PRIMARY KEY (carte_id, utilisateur_id, role)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_collab_carte_membre_carte ON collab_carte_membre(carte_id)")

    # 9) Checklist item assignee on the login account too (0096 pointed to membre).
    op.execute("ALTER TABLE collab_checklist_item DROP COLUMN IF EXISTS assigne_id")
    op.execute(
        "ALTER TABLE collab_checklist_item ADD COLUMN assigne_id uuid "
        "REFERENCES utilisateur(id) ON DELETE SET NULL"
    )

    # 10) Backfill: a default "Comite" space adopts every existing board, and each
    #     active committee account becomes a member, so no board and no access is
    #     lost by introducing the space layer.
    op.execute(
        "INSERT INTO collab_espace (nom, description, type, couleur, initiale, "
        "invitation_jeton, observateurs_commentent) "
        "VALUES ('Comité', 'Espace général du comité', 'autre', '#2A4FAD', 'C', "
        f"'{DEFAULT_TOKEN}', true) "
        "ON CONFLICT (invitation_jeton) DO NOTHING"
    )
    op.execute(
        "UPDATE collab_tableau SET espace_id = "
        f"(SELECT id FROM collab_espace WHERE invitation_jeton = '{DEFAULT_TOKEN}') "
        "WHERE espace_id IS NULL"
    )
    op.execute(
        "INSERT INTO collab_espace_membre (espace_id, utilisateur_id, role) "
        f"SELECT (SELECT id FROM collab_espace WHERE invitation_jeton = '{DEFAULT_TOKEN}'), u.id, "
        "CASE WHEN u.role = 'super_admin' THEN 'proprietaire' "
        "     WHEN u.role = 'admin' THEN 'admin' "
        "     WHEN u.role = 'direction' THEN 'observateur' "
        "     ELSE 'membre' END "
        "FROM utilisateur u "
        "WHERE u.role IN ('super_admin', 'admin', 'gestionnaire', 'direction') AND u.actif = true "
        "ON CONFLICT (espace_id, utilisateur_id) DO NOTHING"
    )
    # Every board now has a space; enforce it at the schema level.
    op.execute("ALTER TABLE collab_tableau ALTER COLUMN espace_id SET NOT NULL")

    op.execute("CREATE INDEX IF NOT EXISTS idx_collab_espace_membre_util ON collab_espace_membre(utilisateur_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_collab_demande_espace ON collab_demande_acces(espace_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_collab_tableau_espace ON collab_tableau(espace_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_collab_tableau_participant_tab "
        "ON collab_tableau_participant(tableau_id)"
    )

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
    for table in NEW_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_select ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_write ON {table}")
    op.execute("ALTER TABLE collab_checklist_item DROP COLUMN IF EXISTS assigne_id")
    op.execute("ALTER TABLE collab_checklist_item ADD COLUMN assigne_id uuid REFERENCES membre(id) ON DELETE SET NULL")
    op.execute("DROP TABLE IF EXISTS collab_carte_membre CASCADE")
    op.execute(
        """
        CREATE TABLE collab_carte_membre (
            carte_id uuid NOT NULL REFERENCES collab_carte(id) ON DELETE CASCADE,
            membre_id uuid NOT NULL REFERENCES membre(id) ON DELETE CASCADE,
            role text NOT NULL DEFAULT 'assigne',
            PRIMARY KEY (carte_id, membre_id, role)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_collab_carte_membre_carte ON collab_carte_membre(carte_id)")
    op.execute("ALTER TABLE collab_carte_membre ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY collab_carte_membre_select ON collab_carte_membre FOR SELECT "
        f"USING (adsum_current_role() = ANY({LECTURE}))"
    )
    op.execute(
        "CREATE POLICY collab_carte_membre_write ON collab_carte_membre FOR ALL "
        f"USING (adsum_current_role() = ANY({COMITE})) "
        f"WITH CHECK (adsum_current_role() = ANY({COMITE}))"
    )
    op.execute("DROP INDEX IF EXISTS idx_collab_etiquette_espace")
    op.execute("ALTER TABLE collab_etiquette DROP COLUMN IF EXISTS espace_id")
    op.execute(
        "ALTER TABLE collab_etiquette ADD COLUMN tableau_id uuid "
        "REFERENCES collab_tableau(id) ON DELETE CASCADE"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_collab_etiquette_tableau ON collab_etiquette(tableau_id)")
    op.execute("ALTER TABLE collab_colonne DROP COLUMN IF EXISTS archivee")
    op.execute("ALTER TABLE collab_colonne DROP COLUMN IF EXISTS wip")
    op.execute("ALTER TABLE collab_colonne DROP COLUMN IF EXISTS repliee")
    op.execute("ALTER TABLE collab_colonne DROP COLUMN IF EXISTS couleur")
    op.execute("ALTER TABLE collab_tableau DROP COLUMN IF EXISTS modele")
    op.execute("ALTER TABLE collab_tableau DROP COLUMN IF EXISTS favori")
    op.execute("ALTER TABLE collab_tableau DROP COLUMN IF EXISTS visibilite")
    op.execute("ALTER TABLE collab_tableau DROP COLUMN IF EXISTS espace_id")
    op.execute("DROP TABLE IF EXISTS collab_tableau_participant CASCADE")
    op.execute("DROP TABLE IF EXISTS collab_demande_acces CASCADE")
    op.execute("DROP TABLE IF EXISTS collab_espace_membre CASCADE")
    op.execute("DROP TABLE IF EXISTS collab_espace CASCADE")
