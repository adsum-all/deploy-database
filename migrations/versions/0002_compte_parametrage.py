"""Create account, traceability, settings and campaign tables (8 of 18).

Tables exactly per the DAT: utilisateur, session, audit (range partitioned,
append-only), notification, parametre, import_lot, recensement,
recensement_reponse. Foreign keys added in revision 0003.

Note on audit: the DAT shows ``id bigserial PRIMARY KEY`` together with
``PARTITION BY RANGE (horodatage)``. PostgreSQL requires the partition key to be
part of any primary key or unique constraint on a partitioned table, so the
primary key is (id, horodatage). This preserves the DAT intent (append-only,
monthly partitions, surrogate id) and is valid. See ADR-0001.

Revision ID: 0002_compte_parametrage
Revises: 0001_identite_activite
Create Date: 2026-06-28
"""
from __future__ import annotations

from alembic import op

revision = "0002_compte_parametrage"
down_revision = "0001_identite_activite"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE utilisateur (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            email text UNIQUE NOT NULL,
            hash_mdp text NOT NULL,
            role text NOT NULL,
            membre_id uuid,
            actif boolean NOT NULL DEFAULT true,
            double_facteur boolean NOT NULL DEFAULT true,
            dernier_login timestamptz,
            cree_le timestamptz DEFAULT now(),
            CONSTRAINT utilisateur_role_chk CHECK (
                role IN ('super_admin', 'admin', 'gestionnaire', 'controleur', 'direction')
            )
        )
        """
    )

    op.execute(
        """
        CREATE TABLE session (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            utilisateur_id uuid,
            jeton_hash text,
            ip inet,
            geo text,
            appareil text,
            cree_le timestamptz DEFAULT now(),
            expire_le timestamptz,
            revoque boolean NOT NULL DEFAULT false
        )
        """
    )

    op.execute(
        """
        CREATE TABLE audit (
            id bigserial,
            acteur_id uuid,
            acteur_role text,
            action text NOT NULL,
            objet_type text,
            objet_id uuid,
            details jsonb,
            ip inet,
            horodatage timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (id, horodatage)
        ) PARTITION BY RANGE (horodatage)
        """
    )

    op.execute(
        """
        CREATE TABLE notification (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            membre_id uuid,
            type text,
            titre text,
            corps text,
            lu boolean NOT NULL DEFAULT false,
            cree_le timestamptz DEFAULT now(),
            envoye_le timestamptz
        )
        """
    )

    op.execute(
        """
        CREATE TABLE parametre (
            cle text PRIMARY KEY,
            valeur jsonb NOT NULL,
            categorie text,
            description text,
            maj_par uuid,
            maj_le timestamptz DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE import_lot (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            fichier text,
            lignes_total int,
            crees int,
            doublons int,
            anomalies int,
            rapport jsonb,
            importe_par uuid,
            importe_le timestamptz DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE recensement (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            annee int UNIQUE NOT NULL,
            ouvert_le timestamptz,
            clos_le timestamptz,
            statut text NOT NULL DEFAULT 'ouvert',
            CONSTRAINT recensement_statut_chk CHECK (statut IN ('ouvert', 'clos'))
        )
        """
    )

    op.execute(
        """
        CREATE TABLE recensement_reponse (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            recensement_id uuid,
            membre_id uuid,
            reponses jsonb,
            soumis_le timestamptz,
            CONSTRAINT recensement_reponse_uniq UNIQUE (recensement_id, membre_id)
        )
        """
    )


def downgrade() -> None:
    for table in (
        "recensement_reponse",
        "recensement",
        "import_lot",
        "parametre",
        "notification",
        "audit",
        "session",
        "utilisateur",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
