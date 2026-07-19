# ruff: noqa: E501 - migrations carry long SQL lines
"""Vice functions, function ranks and the interim (suppleance) model.

Three pieces the hierarchy needs:
- vice_coordinateur / vice_intendant added to the function catalogue (category
  'fonction'), so a vice can be assigned and shown as support, not a permanent N+1.
- niveau_hierarchique back-filled per function (lower = higher authority), so chains
  and the primary position can be ordered by the function's real rank instead of the
  coarse per-family niveau.
- organisation_interim: a dated, audited temporary stand-in (a suppleant covering an
  unavailable titulaire on a function/perimeter), so the N+1 can reflect an active
  interim and be restored automatically when it ends.

Revision ID: 0164_vice_fonctions_interim
Revises: 0163_collab_modele_perso_global
Create Date: 2026-07-19
"""
from __future__ import annotations

from alembic import op

revision = "0164_vice_fonctions_interim"
down_revision = "0163_collab_modele_perso_global"
branch_labels = None
depends_on = None

_COMITE = "ARRAY['super_admin', 'admin', 'gestionnaire']::text[]"
_LECTURE = "ARRAY['super_admin', 'admin', 'gestionnaire', 'direction']::text[]"


def upgrade() -> None:
    # 1) Vice functions in the catalogue (gendered labels, ordinary 'fonction' category).
    op.execute(
        "INSERT INTO fonction_honorifique (cle, libelle_h, libelle_f, libelle_n, categorie, ordre, niveau, transversal, abreviation, actif) VALUES "
        "('vice_coordinateur', 'Vice-coordinateur', 'Vice-coordinatrice', 'Vice-coordination', 'fonction', 65, 30, false, 'VC', true), "
        "('vice_intendant', 'Vice-intendant', 'Vice-intendante', 'Vice-intendance', 'fonction', 66, 30, false, 'VI', true) "
        "ON CONFLICT (cle) DO NOTHING"
    )

    # 2) Fine per-function rank (lower = higher authority) so chains order correctly.
    op.execute(
        "UPDATE fonction_honorifique SET niveau_hierarchique = CASE lower(cle) "
        "WHEN 'fondateur' THEN 1 WHEN 'moderateur' THEN 2 WHEN 'berger_missions' THEN 3 "
        "WHEN 'controleur_general' THEN 4 WHEN 'intendant_general' THEN 5 "
        "WHEN 'intendant' THEN 6 WHEN 'coordinateur' THEN 6 "
        "WHEN 'vice_intendant' THEN 7 WHEN 'vice_coordinateur' THEN 7 "
        "WHEN 'responsable' THEN 8 WHEN 'sous_responsable' THEN 9 "
        "ELSE niveau_hierarchique END "
        "WHERE lower(cle) IN ('fondateur','moderateur','berger_missions','controleur_general','intendant_general','intendant','coordinateur','vice_intendant','vice_coordinateur','responsable','sous_responsable')"
    )

    # 3) Interim / suppleance ledger.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS organisation_interim (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            fonction_cle text NOT NULL,
            perimetre text,
            titulaire_id uuid REFERENCES membre(id) ON DELETE SET NULL,
            suppleant_id uuid NOT NULL REFERENCES membre(id) ON DELETE CASCADE,
            motif text,
            date_debut date NOT NULL DEFAULT current_date,
            date_fin date,
            statut text NOT NULL DEFAULT 'actif',
            cree_par uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            cree_le timestamptz NOT NULL DEFAULT now(),
            maj_le timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT organisation_interim_statut_chk CHECK (statut IN ('actif', 'termine', 'annule')),
            CONSTRAINT organisation_interim_dates_chk CHECK (date_fin IS NULL OR date_fin >= date_debut)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_organisation_interim_suppleant ON organisation_interim(suppleant_id) WHERE statut = 'actif'")
    op.execute("CREATE INDEX IF NOT EXISTS idx_organisation_interim_fonction ON organisation_interim(lower(fonction_cle)) WHERE statut = 'actif'")
    op.execute("ALTER TABLE organisation_interim ENABLE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY organisation_interim_select ON organisation_interim FOR SELECT USING (adsum_current_role() = ANY({_LECTURE}))")
    op.execute(f"CREATE POLICY organisation_interim_write ON organisation_interim FOR ALL USING (adsum_current_role() = ANY({_COMITE})) WITH CHECK (adsum_current_role() = ANY({_COMITE}))")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS organisation_interim")
    op.execute("UPDATE fonction_honorifique SET niveau_hierarchique = NULL WHERE lower(cle) IN ('fondateur','moderateur','berger_missions','controleur_general','intendant_general','intendant','coordinateur','vice_intendant','vice_coordinateur','responsable','sous_responsable')")
    op.execute("DELETE FROM fonction_honorifique WHERE cle IN ('vice_coordinateur', 'vice_intendant')")
