# ruff: noqa: E501 - migrations carry long SQL lines
"""Give collaboration templates a life cycle and rights of their own.

Creating a board template was governed by a single coarse permission,
``collaboration.modeles``, which bundled creating, editing and deleting. Anyone
allowed to prepare a template was therefore also allowed to remove one, and nothing
distinguished a draft from a template the organisation actually stands behind.

Templates now have a state: a draft is prepared, a published one is offered to the
teams, an archived one stops being offered without being destroyed, since boards
already created from it must keep working. Each transition has its own permission,
so preparing, approving and removing can be held by different people, and five
standard groups make the usual combinations available without hand-picking rights.

Revision ID: 0175_templates_collaboration
Revises: 0174_permissions_referentiel
Create Date: 2026-07-26
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0175_templates_collaboration"
down_revision = "0174_permissions_referentiel"
branch_labels = None
depends_on = None

# cle -> (libelle, description, risque)
_PERMISSIONS = {
    "collaboration.template.read": (
        "Modèles de collaboration - consulter",
        "Voir le catalogue des modèles de tableaux et le détail de leur structure.",
        "faible",
    ),
    "collaboration.template.use": (
        "Modèles de collaboration - utiliser",
        "Créer un tableau à partir d'un modèle publié, sans pouvoir modifier le modèle lui-même.",
        "faible",
    ),
    "collaboration.template.create": (
        "Modèles de collaboration - créer",
        "Préparer un nouveau modèle de tableau, qui reste à l'état de brouillon jusqu'à sa publication.",
        "moyen",
    ),
    "collaboration.template.update": (
        "Modèles de collaboration - modifier",
        "Modifier la structure, le nom ou la description d'un modèle existant.",
        "moyen",
    ),
    "collaboration.template.publish": (
        "Modèles de collaboration - publier",
        "Publier un brouillon, ce qui le met à disposition des équipes, ou le renvoyer en brouillon.",
        "eleve",
    ),
    "collaboration.template.archive": (
        "Modèles de collaboration - archiver",
        "Retirer un modèle du catalogue sans le détruire ; les tableaux déjà créés restent intacts.",
        "moyen",
    ),
    "collaboration.template.delete": (
        "Modèles de collaboration - supprimer",
        "Supprimer définitivement un modèle. Les tableaux issus de ce modèle ne sont pas affectés.",
        "eleve",
    ),
    "collaboration.template.manage-all": (
        "Modèles de collaboration - administrer",
        "Administrer tous les modèles, y compris ceux dont on n'est pas l'auteur, sur l'ensemble du catalogue.",
        "eleve",
    ),
}

# Standard groups: the usual combinations, so the rights need not be picked one by one.
_GROUPES = {
    "modeles_lecteur": (
        "Lecteur de modèles",
        "Consulter le catalogue des modèles de tableaux, sans pouvoir en utiliser ni en modifier.",
        ["collaboration.template.read"],
        "faible",
    ),
    "modeles_utilisateur": (
        "Utilisateur de modèles",
        "Créer des tableaux à partir des modèles publiés, sans toucher aux modèles eux-mêmes.",
        ["collaboration.template.read", "collaboration.template.use"],
        "faible",
    ),
    "modeles_createur": (
        "Créateur de modèles",
        "Préparer et modifier des modèles, qui restent des brouillons tant qu'un valideur ne les publie pas.",
        ["collaboration.template.read", "collaboration.template.use",
         "collaboration.template.create", "collaboration.template.update"],
        "moyen",
    ),
    "modeles_validateur": (
        "Validateur de modèles",
        "Publier les brouillons préparés par les créateurs et archiver les modèles devenus obsolètes.",
        ["collaboration.template.read", "collaboration.template.use",
         "collaboration.template.publish", "collaboration.template.archive"],
        "eleve",
    ),
    "modeles_administrateur": (
        "Administrateur des modèles",
        "Administrer l'ensemble du catalogue des modèles, y compris la suppression définitive.",
        list(_PERMISSIONS),
        "eleve",
    ),
}

_DOC_GROUPES = {
    "modeles_lecteur": ("Pour un observateur qui doit connaître les modèles disponibles.",
                        "Ne pas utiliser si la personne doit créer des tableaux : ajouter l'usage."),
    "modeles_utilisateur": ("Pour toute équipe qui monte ses tableaux à partir du catalogue.",
                           "Ne pas utiliser pour préparer de nouveaux modèles."),
    "modeles_createur": ("Pour les personnes qui conçoivent les modèles de l'organisation.",
                        "Ne donne pas le droit de publier : la mise à disposition reste un acte distinct."),
    "modeles_validateur": ("Pour la personne qui approuve ce que l'organisation met à disposition.",
                          "Ne permet pas de créer ni de modifier un modèle, pour séparer la préparation de l'approbation."),
    "modeles_administrateur": ("Pour l'administration du catalogue, y compris la suppression.",
                              "Ne pas accorder pour un simple usage courant des modèles."),
}


def _lit(v: str) -> str:
    return "'" + v.replace("'", "''") + "'"


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Life cycle of a template.
    op.execute(
        """
        ALTER TABLE collab_modele_perso
            ADD COLUMN IF NOT EXISTS statut text NOT NULL DEFAULT 'publie',
            ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1,
            ADD COLUMN IF NOT EXISTS publie_le timestamptz,
            ADD COLUMN IF NOT EXISTS publie_par uuid,
            ADD COLUMN IF NOT EXISTS archive_le timestamptz,
            ADD COLUMN IF NOT EXISTS archive_par uuid
        """
    )
    op.execute("ALTER TABLE collab_modele_perso DROP CONSTRAINT IF EXISTS collab_modele_statut_check")
    op.execute(
        "ALTER TABLE collab_modele_perso ADD CONSTRAINT collab_modele_statut_check "
        "CHECK (statut IN ('brouillon', 'publie', 'archive'))"
    )
    # Templates already in the library were usable, so they stay published.
    op.execute("UPDATE collab_modele_perso SET publie_le = COALESCE(publie_le, cree_le) WHERE statut = 'publie'")
    op.execute("CREATE INDEX IF NOT EXISTS idx_collab_modele_statut ON collab_modele_perso (statut)")

    # 2. The eight permissions, in one statement each (pooler-safe).
    valeurs = ", ".join(
        f"({_lit(cle)}, 'collaboration', {_lit(lib)}, {_lit(desc)}, {_lit(risque)}, 'global', true)"
        for cle, (lib, desc, risque) in _PERMISSIONS.items()
    )
    bind.execute(sa.text(
        "INSERT INTO permission (cle, domaine, libelle, description, risque, portee, systeme) "
        f"VALUES {valeurs} ON CONFLICT (cle) DO NOTHING"
    ))

    # Whoever already administered templates keeps every new right, so nobody loses
    # a capability at the moment the coarse permission is split.
    roles_admin = ("admin", "super_admin")
    paires = ", ".join(f"({_lit(r)}, {_lit(p)})" for r in roles_admin for p in _PERMISSIONS)
    bind.execute(sa.text(f"INSERT INTO role_permission (role, permission) VALUES {paires} ON CONFLICT DO NOTHING"))
    # A collaborator reads and uses the catalogue; preparing a model is a separate act.
    lecture = ", ".join(
        f"({_lit(r)}, {_lit(p)})"
        for r in ("gestionnaire", "direction")
        for p in ("collaboration.template.read", "collaboration.template.use")
    )
    bind.execute(sa.text(f"INSERT INTO role_permission (role, permission) VALUES {lecture} ON CONFLICT DO NOTHING"))

    # 3. The five standard groups.
    for cle, (libelle, finalite, perms, sensibilite) in _GROUPES.items():
        recommande, deconseille = _DOC_GROUPES[cle]
        bind.execute(sa.text(
            "INSERT INTO groupe_acces (cle, libelle, description, role_accorde, systeme, mode, application_code, "
            "finalite, usage_recommande, usage_deconseille, portee_texte, sensibilite) "
            f"VALUES ({_lit(cle)}, {_lit(libelle)}, {_lit(finalite)}, 'membre', true, 'permissions', 'collaboration', "
            f"{_lit(finalite)}, {_lit(recommande)}, {_lit(deconseille)}, "
            "'Catalogue des modèles de tableaux de la collaboration.', "
            f"{_lit(sensibilite)}) ON CONFLICT (cle) DO NOTHING"
        ))
        liens = ", ".join(f"(g.id, {_lit(p)})" for p in perms)
        bind.execute(sa.text(
            f"INSERT INTO groupe_permission (groupe_id, permission) SELECT g.id, v.p "
            f"FROM groupe_acces g, (VALUES {', '.join(f'({_lit(p)})' for p in perms)}) AS v(p) "
            f"WHERE g.cle = {_lit(cle)} ON CONFLICT DO NOTHING"
        ))


def downgrade() -> None:
    cles = ", ".join(_lit(c) for c in _GROUPES)
    op.execute(f"DELETE FROM groupe_acces WHERE cle IN ({cles}) AND systeme = true")
    perms = ", ".join(_lit(p) for p in _PERMISSIONS)
    op.execute(f"DELETE FROM role_permission WHERE permission IN ({perms})")
    op.execute(f"DELETE FROM permission WHERE cle IN ({perms})")
    op.execute("DROP INDEX IF EXISTS idx_collab_modele_statut")
    op.execute("ALTER TABLE collab_modele_perso DROP CONSTRAINT IF EXISTS collab_modele_statut_check")
    op.execute(
        """
        ALTER TABLE collab_modele_perso
            DROP COLUMN IF EXISTS statut,
            DROP COLUMN IF EXISTS version,
            DROP COLUMN IF EXISTS publie_le,
            DROP COLUMN IF EXISTS publie_par,
            DROP COLUMN IF EXISTS archive_le,
            DROP COLUMN IF EXISTS archive_par
        """
    )
