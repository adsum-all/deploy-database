# ruff: noqa: E501 - migrations carry long SQL lines
"""Realign the permission table with the enforced catalogue.

``groupe_permission.permission`` carries a foreign key to ``permission(cle)``, so a
permission that exists in the code catalogue but not in that table cannot be granted
to any group: the insert is refused by the database. Two keys were in that state,
``informations.consulter`` and ``informations.gerer``, added to the catalogue when
the Informations module shipped but never inserted in the table.

The consequence was not theoretical. Every write path that stores a permission set
failed on those two keys, and duplicating the "Administration" or
"Super administration" standard group was a certain failure, since both grant them.

The rows are inserted from the same values the catalogue declares, so the table and
the code state exactly the same thing. Also refreshes the labels, which 0170 and the
catalogue re-accented while the table kept the unaccented wording.

Revision ID: 0174_permissions_referentiel
Revises: 0173_groupes_standard_finalite
Create Date: 2026-07-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0174_permissions_referentiel"
down_revision = "0173_groupes_standard_finalite"
branch_labels = None
depends_on = None

# cle -> (domaine, libelle, risque, portee)
_MANQUANTES = {
    "informations.consulter": ("communication", "Informations - consulter", "faible", "global"),
    "informations.gerer": ("communication", "Informations - diffuser", "eleve", "global"),
}

# Labels re-accented in the catalogue, to mirror in the table.
_LIBELLES = {
    "acces.administrer": "Accès et groupes - administrer",
    "acces.systeme": "Accès et groupes - administration système",
    "comptage.controler": "Comptage - contrôler",
    "comptes.systeme": "Comptes - administration système",
    "controle.controler": "Contrôle - contrôler",
    "deblocage.superviser": "Déblocage - superviser",
    "evenements.consulter": "Événements - consulter",
    "evenements.gerer": "Événements - gérer",
    "evenements.superviser": "Événements - superviser",
    "integrations.administrer": "Intégrations - administrer",
    "integrations.superviser": "Intégrations - superviser",
    "membres.self": "Membres - accès personnel",
    "modeles.consulter": "Modèles - consulter",
    "modeles.gerer": "Modèles - gérer",
    "parametres.consulter": "Paramètres - consulter",
    "parametres.gerer": "Paramètres - gérer",
    "tags.administrer": "Étiquettes - administrer",
    "collaboration.modeles": "Collaboration - modèles de tableaux",
}


def _litteral(v: str) -> str:
    return "'" + v.replace("'", "''") + "'"


def upgrade() -> None:
    bind = op.get_bind()
    # One statement per batch, not one per row: over the Supabase transaction pooler a
    # named prepared statement left on a reused backend collides with the next call
    # ("_pg3_0 already exists"), so a repeated parameterised execute is not reliable.
    valeurs = ", ".join(
        f"({_litteral(cle)}, {_litteral(d)}, {_litteral(lib)}, {_litteral(r)}, {_litteral(p)}, true)"
        for cle, (d, lib, r, p) in _MANQUANTES.items()
    )
    bind.execute(sa.text(
        "INSERT INTO permission (cle, domaine, libelle, risque, portee, systeme) "
        f"VALUES {valeurs} ON CONFLICT (cle) DO NOTHING"
    ))

    maj = ", ".join(f"({_litteral(cle)}, {_litteral(lib)})" for cle, lib in _LIBELLES.items())
    bind.execute(sa.text(
        f"UPDATE permission p SET libelle = v.libelle FROM (VALUES {maj}) AS v(cle, libelle) WHERE p.cle = v.cle"
    ))

    # The two keys belong to the roles that already hold them in the code mapping, so
    # the table-driven view of the roles stops contradicting the enforced one.
    bind.execute(sa.text(
        "INSERT INTO role_permission (role, permission) "
        "SELECT r.role, p.cle FROM (VALUES ('admin'), ('super_admin'), ('gestionnaire')) AS r(role), "
        "(VALUES ('informations.consulter'), ('informations.gerer')) AS p(cle) "
        "ON CONFLICT DO NOTHING"
    ))
    bind.execute(sa.text(
        "INSERT INTO role_permission (role, permission) VALUES ('direction', 'informations.consulter') "
        "ON CONFLICT DO NOTHING"
    ))


def downgrade() -> None:
    op.execute("DELETE FROM role_permission WHERE permission IN ('informations.consulter', 'informations.gerer')")
    op.execute("DELETE FROM permission WHERE cle IN ('informations.consulter', 'informations.gerer')")
