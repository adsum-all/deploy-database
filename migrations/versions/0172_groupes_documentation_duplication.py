# ruff: noqa: E501 - migrations carry long SQL lines
"""Document access groups and let a standard one be duplicated into a custom one.

Two needs are covered.

Documentation. A group used to carry a label and a free description, which left an
administrator guessing what granting it actually means. The added columns state the
purpose, when to use it and when not to, the organisational scope, the sensitivity
level and the security warning, plus authorship and last-change tracking. The
history itself is not duplicated: the ``audit`` table already records creation,
modification, deletion and membership changes for ``groupe_acces``, so the group
sheet reads it back rather than keeping a second, divergent copy.

Duplication. A system group is protected and cannot be edited. An administrator must
still be able to start from that reliable base, so a standard group can be copied
into a custom one that remembers where it came from (``source_standard_group_id``)
and at which template version (``source_version``). The copy is editable; comparing
it to its source is then a matter of diffing permissions, which needs no extra
storage.

Membership rows gain the role held inside the group and an explicit active flag, so
removing someone keeps a dated trace instead of erasing the fact.

Revision ID: 0172_groupes_doc_duplication
Revises: 0171_responsable_unite_membre
Create Date: 2026-07-24
"""
from __future__ import annotations

from alembic import op

revision = "0172_groupes_doc_duplication"
down_revision = "0171_responsable_unite_membre"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE groupe_acces
            ADD COLUMN IF NOT EXISTS finalite text,
            ADD COLUMN IF NOT EXISTS usage_recommande text,
            ADD COLUMN IF NOT EXISTS usage_deconseille text,
            ADD COLUMN IF NOT EXISTS portee_texte text,
            ADD COLUMN IF NOT EXISTS sensibilite text NOT NULL DEFAULT 'moyen',
            ADD COLUMN IF NOT EXISTS avertissement_securite text,
            ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1,
            ADD COLUMN IF NOT EXISTS cree_par uuid,
            ADD COLUMN IF NOT EXISTS maj_le timestamptz,
            ADD COLUMN IF NOT EXISTS maj_par uuid,
            ADD COLUMN IF NOT EXISTS source_standard_group_id uuid,
            ADD COLUMN IF NOT EXISTS derived_from_standard boolean NOT NULL DEFAULT false,
            ADD COLUMN IF NOT EXISTS source_version integer,
            ADD COLUMN IF NOT EXISTS inheritance_mode text NOT NULL DEFAULT 'copie',
            ADD COLUMN IF NOT EXISTS custom_scope text
        """
    )
    op.execute(
        "ALTER TABLE groupe_acces DROP CONSTRAINT IF EXISTS groupe_acces_sensibilite_check"
    )
    op.execute(
        "ALTER TABLE groupe_acces ADD CONSTRAINT groupe_acces_sensibilite_check "
        "CHECK (sensibilite IN ('faible', 'moyen', 'eleve', 'critique'))"
    )
    op.execute(
        "ALTER TABLE groupe_acces DROP CONSTRAINT IF EXISTS groupe_acces_inheritance_check"
    )
    op.execute(
        "ALTER TABLE groupe_acces ADD CONSTRAINT groupe_acces_inheritance_check "
        "CHECK (inheritance_mode IN ('copie', 'lie'))"
    )
    # A derived group points at the standard it was copied from. Deleting the source
    # must not delete the copy: the link is simply forgotten.
    op.execute("ALTER TABLE groupe_acces DROP CONSTRAINT IF EXISTS groupe_acces_source_standard_fk")
    op.execute(
        "ALTER TABLE groupe_acces ADD CONSTRAINT groupe_acces_source_standard_fk "
        "FOREIGN KEY (source_standard_group_id) REFERENCES groupe_acces(id) ON DELETE SET NULL"
    )
    # A copy must declare its source, and a source is only ever a system group. The
    # check stays on the flag pair so a custom group cannot claim a lineage it has not.
    op.execute("ALTER TABLE groupe_acces DROP CONSTRAINT IF EXISTS groupe_acces_derive_coherent_check")
    op.execute(
        "ALTER TABLE groupe_acces ADD CONSTRAINT groupe_acces_derive_coherent_check "
        "CHECK (derived_from_standard = false OR source_standard_group_id IS NOT NULL)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_groupe_acces_source ON groupe_acces (source_standard_group_id)")

    # Sensitivity of the system groups, from what each one actually grants.
    op.execute("UPDATE groupe_acces SET sensibilite = 'critique' WHERE systeme = true AND cle IN ('super_administration', 'administration', 'administrateur_delegue')")
    op.execute("UPDATE groupe_acces SET sensibilite = 'eleve' WHERE systeme = true AND cle IN ('gestion_membres', 'editeur_membres', 'operateur_inscriptions', 'gestionnaire_evenements')")
    op.execute("UPDATE groupe_acces SET sensibilite = 'faible' WHERE systeme = true AND cle IN ('lecteur_statistiques', 'auditeur')")

    op.execute(
        """
        ALTER TABLE membre_groupe
            ADD COLUMN IF NOT EXISTS role_interne text,
            ADD COLUMN IF NOT EXISTS actif boolean NOT NULL DEFAULT true,
            ADD COLUMN IF NOT EXISTS retire_le timestamptz,
            ADD COLUMN IF NOT EXISTS retire_par uuid
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_membre_groupe_actif ON membre_groupe (groupe_id, actif)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_membre_groupe_actif")
    op.execute(
        """
        ALTER TABLE membre_groupe
            DROP COLUMN IF EXISTS role_interne,
            DROP COLUMN IF EXISTS actif,
            DROP COLUMN IF EXISTS retire_le,
            DROP COLUMN IF EXISTS retire_par
        """
    )
    op.execute("DROP INDEX IF EXISTS idx_groupe_acces_source")
    op.execute("ALTER TABLE groupe_acces DROP CONSTRAINT IF EXISTS groupe_acces_derive_coherent_check")
    op.execute("ALTER TABLE groupe_acces DROP CONSTRAINT IF EXISTS groupe_acces_source_standard_fk")
    op.execute("ALTER TABLE groupe_acces DROP CONSTRAINT IF EXISTS groupe_acces_inheritance_check")
    op.execute("ALTER TABLE groupe_acces DROP CONSTRAINT IF EXISTS groupe_acces_sensibilite_check")
    op.execute(
        """
        ALTER TABLE groupe_acces
            DROP COLUMN IF EXISTS finalite,
            DROP COLUMN IF EXISTS usage_recommande,
            DROP COLUMN IF EXISTS usage_deconseille,
            DROP COLUMN IF EXISTS portee_texte,
            DROP COLUMN IF EXISTS sensibilite,
            DROP COLUMN IF EXISTS avertissement_securite,
            DROP COLUMN IF EXISTS version,
            DROP COLUMN IF EXISTS cree_par,
            DROP COLUMN IF EXISTS maj_le,
            DROP COLUMN IF EXISTS maj_par,
            DROP COLUMN IF EXISTS source_standard_group_id,
            DROP COLUMN IF EXISTS derived_from_standard,
            DROP COLUMN IF EXISTS source_version,
            DROP COLUMN IF EXISTS inheritance_mode,
            DROP COLUMN IF EXISTS custom_scope
        """
    )
