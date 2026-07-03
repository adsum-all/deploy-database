# ruff: noqa: E501 - migrations carry long SQL and seeded text lines
"""Honorific function catalogue and member function assignment.

Members with an important function (Berger, Coordinateur, Intendant, Moderateur,
BSG, Patriarche, Fondateur, ...) must show that title before their name, resolved
by gender. The catalogue lives in an admin-editable table so the administration
can add, rename or retire a function without a redeployment. A member declares
their function at registration (self-service) but the honorific prefix is only
shown to others once an administrator has confirmed it, so no one can display an
unearned title. The engagement status enum is widened to the terms used in the
registration form (membre actif, inspirant).

Revision ID: 0026_membre_fonction
Revises: 0025_integration_config
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0026_membre_fonction"
down_revision = "0025_integration_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Editable catalogue of honorific functions. libelle_h / libelle_f / libelle_n
    # are the masculine, feminine and epicene (gender-unknown) prefixes.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS fonction_honorifique (
            cle text PRIMARY KEY,
            libelle_h text NOT NULL,
            libelle_f text NOT NULL,
            libelle_n text NOT NULL,
            est_vip boolean NOT NULL DEFAULT false,
            ordre integer NOT NULL DEFAULT 100,
            actif boolean NOT NULL DEFAULT true,
            maj_par uuid,
            maj_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    # Seed the known functions. est_vip drives the default calendar visibility.
    op.execute(
        """
        INSERT INTO fonction_honorifique (cle, libelle_h, libelle_f, libelle_n, est_vip, ordre) VALUES
            ('fondateur',       'Fondateur',            'Fondatrice',            'Fondateur',            true,  10),
            ('moderateur',      'Moderateur',           'Moderatrice',           'Moderateur',           true,  20),
            ('bsg_missions',    'BSG des missions',     'BSG des missions',      'BSG des missions',     true,  30),
            ('bsg',             'BSG',                  'BSG',                   'BSG',                  true,  40),
            ('coordinateur',    'Coordinateur',         'Coordinatrice',         'Coordination',         true,  50),
            ('intendant',       'Intendant',            'Intendante',            'Intendant',            true,  60),
            ('patriarche',      'Patriarche',           'Patriarche',            'Patriarche',           true,  70),
            ('berger_missions', 'Berger des missions',  'Bergere des missions',  'Berger des missions',  true,  80),
            ('berger',          'Berger',               'Bergere',               'Berger',               true,  90),
            ('responsable',     'Responsable',          'Responsable',           'Responsable',          false, 100)
        ON CONFLICT (cle) DO NOTHING
        """
    )
    # Member assignment: declared function plus an admin-confirmed flag.
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS fonction_cle text")
    op.execute("ALTER TABLE membre ADD COLUMN IF NOT EXISTS fonction_confirmee boolean NOT NULL DEFAULT false")
    # Widen the engagement enum with the registration-form terms.
    op.execute("ALTER TABLE membre DROP CONSTRAINT IF EXISTS membre_type_membre_chk")
    op.execute(
        """
        ALTER TABLE membre ADD CONSTRAINT membre_type_membre_chk CHECK (
            type_membre IN ('membre_simple','membre_actif','nouveau_engage','aspirant','engage','inspirant','berger','responsable')
        )
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE membre DROP CONSTRAINT IF EXISTS membre_type_membre_chk")
    op.execute(
        """
        ALTER TABLE membre ADD CONSTRAINT membre_type_membre_chk CHECK (
            type_membre IN ('membre_simple','nouveau_engage','aspirant','engage','berger','responsable')
        )
        """
    )
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS fonction_confirmee")
    op.execute("ALTER TABLE membre DROP COLUMN IF EXISTS fonction_cle")
    op.execute("DROP TABLE IF EXISTS fonction_honorifique")
