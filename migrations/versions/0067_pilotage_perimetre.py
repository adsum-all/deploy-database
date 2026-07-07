# ruff: noqa: E501 - migrations carry long SQL and seeded text lines
"""Pilotage layer tables: governed tags and perimeter consultations (surveys).

Additive tables for the responsable-de-perimetre pilotage: a governed tag
catalogue (families, not free text) with a request/validation workflow and an
event tagging link, and a consultation (survey) engine with questions and
single-answer-per-member responses. Row level security is enabled with the same
adsum_current_role() policy pattern as the rest of the schema (defence in depth;
the application access is owner-bypassed and enforced at the API scope layer).
Also seeds the responsable_pays and responsable_continental honorific functions
used to derive attribute-based perimeters.

Revision ID: 0067_pilotage_perimetre
Revises: 0066_coord_intendance_enrichie
Create Date: 2026-07-05
"""
from __future__ import annotations

from alembic import op

revision = "0067_pilotage_perimetre"
down_revision = "0066_coord_intendance_enrichie"
branch_labels = None
depends_on = None

# New tables in creation order (respecting FK dependencies).
_TABLES = [
    "tag",
    "evenement_tag",
    "tag_demande",
    "consultation",
    "consultation_question",
    "consultation_reponse",
]

# adsum_current_role() access matrix for the new tables (select_roles, write_roles).
_SELECT = ["super_admin", "admin", "gestionnaire", "controleur", "direction"]
_WRITE = ["super_admin", "admin"]


def _array(roles: list[str]) -> str:
    return "ARRAY[" + ", ".join(f"'{r}'" for r in roles) + "]::text[]"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE tag (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            cle text NOT NULL UNIQUE,
            libelle text NOT NULL,
            famille text NOT NULL,
            niveau_gouvernance text NOT NULL DEFAULT 'central',
            description text,
            actif boolean NOT NULL DEFAULT true,
            cree_le timestamptz DEFAULT now(),
            CONSTRAINT tag_famille_chk CHECK (famille IN ('diffusion', 'territoire', 'organisation', 'type_activite', 'transverse')),
            CONSTRAINT tag_gouvernance_chk CHECK (niveau_gouvernance IN ('systeme', 'central', 'perimetre'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE evenement_tag (
            evenement_id uuid NOT NULL REFERENCES evenement(id) ON DELETE CASCADE,
            tag_id uuid NOT NULL REFERENCES tag(id) ON DELETE CASCADE,
            PRIMARY KEY (evenement_id, tag_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE tag_demande (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            proposant_membre_id uuid REFERENCES membre(id) ON DELETE SET NULL,
            famille text NOT NULL,
            libelle text NOT NULL,
            justification text,
            statut text NOT NULL DEFAULT 'nouveau',
            decide_par uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            decide_le timestamptz,
            cree_le timestamptz DEFAULT now(),
            CONSTRAINT tag_demande_statut_chk CHECK (statut IN ('nouveau', 'accepte', 'refuse'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE consultation (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            titre text NOT NULL,
            description text,
            dimension text NOT NULL DEFAULT 'general',
            scope_id uuid,
            evenement_id uuid REFERENCES evenement(id) ON DELETE SET NULL,
            statut text NOT NULL DEFAULT 'brouillon',
            ouverture timestamptz,
            fermeture timestamptz,
            cree_par uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            cree_le timestamptz DEFAULT now(),
            CONSTRAINT consultation_dimension_chk CHECK (dimension IN ('general', 'coordination', 'intendance', 'tribu')),
            CONSTRAINT consultation_statut_chk CHECK (statut IN ('brouillon', 'ouverte', 'close', 'archivee'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE consultation_question (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            consultation_id uuid NOT NULL REFERENCES consultation(id) ON DELETE CASCADE,
            libelle text NOT NULL,
            type text NOT NULL DEFAULT 'choix',
            options jsonb NOT NULL DEFAULT '[]'::jsonb,
            ordre int NOT NULL DEFAULT 0,
            CONSTRAINT consultation_question_type_chk CHECK (type IN ('oui_non', 'choix', 'choix_multiple', 'note', 'texte'))
        )
        """
    )
    op.execute(
        """
        CREATE TABLE consultation_reponse (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            consultation_id uuid NOT NULL REFERENCES consultation(id) ON DELETE CASCADE,
            question_id uuid NOT NULL REFERENCES consultation_question(id) ON DELETE CASCADE,
            membre_id uuid NOT NULL REFERENCES membre(id) ON DELETE CASCADE,
            valeur text,
            canal text NOT NULL DEFAULT 'interne',
            cree_le timestamptz DEFAULT now(),
            CONSTRAINT consultation_reponse_unique UNIQUE (question_id, membre_id)
        )
        """
    )

    op.execute("CREATE INDEX idx_evenement_tag_tag ON evenement_tag(tag_id)")
    op.execute("CREATE INDEX idx_consultation_scope ON consultation(dimension, scope_id)")
    op.execute("CREATE INDEX idx_consultation_reponse_consultation ON consultation_reponse(consultation_id)")

    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY {table}_select ON {table} FOR SELECT USING (adsum_current_role() = ANY({_array(_SELECT)}))")
        op.execute(f"CREATE POLICY {table}_write ON {table} FOR ALL USING (adsum_current_role() = ANY({_array(_WRITE)})) WITH CHECK (adsum_current_role() = ANY({_array(_WRITE)}))")


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.execute(f"DROP POLICY IF EXISTS {table}_write ON {table}")
        op.execute(f"DROP POLICY IF EXISTS {table}_select ON {table}")
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
