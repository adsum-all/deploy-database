"""Create identity and activity tables (10 of 18), no cross-table foreign keys.

Tables exactly per the DAT data model: membre, commission, appartenance,
engagement, document, evenement, terminal, presence, jeton_qr, comptage_volet_b.
Foreign keys are added in revision 0003 to handle the circular references of the
DAT (membre <-> commission, references to utilisateur created in 0002).

Revision ID: 0001_identite_activite
Revises:
Create Date: 2026-06-28
"""
from __future__ import annotations

from alembic import op

revision = "0001_identite_activite"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")  # gen_random_uuid()

    op.execute(
        """
        CREATE TABLE commission (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            nom text NOT NULL,
            responsable_id uuid,
            description text,
            cree_le timestamptz DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE membre (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            matricule text UNIQUE NOT NULL,
            email text UNIQUE NOT NULL,
            nom text,
            prenoms text,
            telephone text,
            adresse text,
            commission_id uuid,
            groupe text,
            photo_url text,
            statut text NOT NULL DEFAULT 'actif',
            verifie boolean NOT NULL DEFAULT false,
            cree_le timestamptz DEFAULT now(),
            desactive_le timestamptz,
            CONSTRAINT membre_statut_chk CHECK (statut IN ('actif', 'inactif', 'suspendu'))
        )
        """
    )

    op.execute(
        """
        CREATE TABLE appartenance (
            membre_id uuid NOT NULL,
            commission_id uuid NOT NULL,
            role_local text,
            depuis_le timestamptz DEFAULT now(),
            PRIMARY KEY (membre_id, commission_id)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE engagement (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            membre_id uuid,
            type text,
            version text NOT NULL,
            signe_le timestamptz,
            hash_preuve text
        )
        """
    )

    op.execute(
        """
        CREATE TABLE document (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            membre_id uuid,
            type text,
            statut text NOT NULL DEFAULT 'demande',
            demande_le timestamptz,
            recu_le timestamptz,
            traite_le timestamptz,
            traite_par uuid,
            CONSTRAINT document_statut_chk CHECK (statut IN ('demande', 'recu', 'lu', 'traite'))
        )
        """
    )

    op.execute(
        """
        CREATE TABLE evenement (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            titre text NOT NULL,
            type text,
            volet text NOT NULL DEFAULT 'A',
            mode text,
            debut timestamptz NOT NULL,
            fin timestamptz,
            lieu text,
            recurrence jsonb,
            serie_id uuid,
            session_ouverte boolean NOT NULL DEFAULT false,
            ouvert_le timestamptz,
            clos_le timestamptz,
            cree_par uuid,
            cree_le timestamptz DEFAULT now(),
            CONSTRAINT evenement_volet_chk CHECK (volet IN ('A', 'B'))
        )
        """
    )

    op.execute(
        """
        CREATE TABLE terminal (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            nom text,
            appareil_id text UNIQUE,
            controleur_id uuid,
            version_cle_pub int,
            autorise boolean NOT NULL DEFAULT false,
            appaire_le timestamptz,
            dernier_sync timestamptz
        )
        """
    )

    op.execute(
        """
        CREATE TABLE presence (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            membre_id uuid,
            evenement_id uuid,
            mode text,
            arrivee timestamptz,
            depart timestamptz,
            methode text,
            terminal_id uuid,
            CONSTRAINT presence_membre_evenement_uniq UNIQUE (membre_id, evenement_id)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE jeton_qr (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            membre_id uuid,
            payload bytea,
            version_cle int,
            revoque boolean NOT NULL DEFAULT false,
            revoque_le timestamptz
        )
        """
    )

    op.execute(
        """
        CREATE TABLE comptage_volet_b (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            evenement_id uuid,
            segment text,
            total_membres int NOT NULL DEFAULT 0,
            total_anonyme int NOT NULL DEFAULT 0,
            saisi_par uuid,
            horodatage timestamptz DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    for table in (
        "comptage_volet_b",
        "jeton_qr",
        "presence",
        "terminal",
        "evenement",
        "document",
        "engagement",
        "appartenance",
        "membre",
        "commission",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
