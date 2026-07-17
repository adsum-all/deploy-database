# ruff: noqa: E501 - migrations carry long SQL lines
"""Administrable referential of activity targeting destinations.

Until now the destination list (general, coordination, commission, intendance,
tribu, bergers, responsables, liste) was a frozen enum: adding a destination
(e.g. "Patriarches") required a code change and a migration. This migration
introduces ``cible_activite``, the referential driving the forms and validation:

- ``code`` is stable and unique (never reused, never renamed); the ``libelle`` can
  be renamed without breaking history or statistics.
- ``type_regle`` is constrained to SAFE templates evaluated server-side (no free
  rules): 'tous' (every active member), 'unite' (members of an organisational
  unit, ``cible_id`` required), 'fonction' (holders of a catalogue function, e.g.
  patriarche), 'attribut' (whitelisted member attribute, e.g. est_berger),
  'liste' (explicit e-mail addresses).
- ``parametres`` is a jsonb validated by the API against the template (e.g.
  {"fonction_cles": ["patriarche"]}).
- ``statut`` actif | inactif | archive: an inactive destination disappears from
  new forms but stays readable on historical activities.

Integrity becomes DATA-driven instead of frozen CHECKs:
- FK ``evenement.cible_type`` -> ``cible_activite(code)`` (replaces the list CHECK).
- Coherence trigger: a 'unite' destination requires ``cible_id``, every other kind
  forbids it (replaces the frozen pair CHECK that would have rejected any new
  destination).

Seed: the 8 existing destinations keep EXACTLY their current codes (zero break for
existing events) plus the "Patriarches" destination grounded on the real source of
truth (catalogue function 'patriarche', active and confirmed; the historical
column tribu.patriarche_membre_id is empty and is NOT the source).

Revision ID: 0147_referentiel_cibles_activite
Revises: 0146_prefs_compte_groupe_app
Create Date: 2026-07-17
"""
from __future__ import annotations

from alembic import op

revision = "0147_referentiel_cibles_activite"
down_revision = "0146_prefs_compte_groupe_app"
branch_labels = None
depends_on = None

_LECTURE = "ARRAY['super_admin', 'admin', 'gestionnaire', 'direction', 'membre', 'controleur']::text[]"
_ECRITURE = "ARRAY['super_admin', 'admin']::text[]"

_SEED = [
    # (code, libelle, description, categorie, type_regle, parametres, ordre)
    ("general", "Toute la communauté (général)", "Tous les membres actifs de la communauté.", "audience", "tous", "{}", 10),
    ("coordination", "Coordination", "Les membres rattachés à la coordination choisie.", "unite", "unite", '{"table": "coordination"}', 20),
    ("commission", "Commission / Mission", "Les membres rattachés à la commission ou mission choisie.", "unite", "unite", '{"table": "commission"}', 30),
    ("intendance", "Intendance", "Les membres rattachés à l'intendance choisie.", "unite", "unite", '{"table": "intendance"}', 40),
    ("tribu", "Tribu", "Les membres rattachés à la tribu choisie.", "unite", "unite", '{"table": "tribu"}', 50),
    ("bergers", "Les Bergers", "Les membres actifs désignés bergers.", "responsabilite", "attribut", '{"attribut": "est_berger"}', 60),
    ("responsables", "Les responsables (avec fonction)", "Les membres actifs détenant au moins une fonction confirmée du catalogue.", "responsabilite", "fonction", '{"toutes_fonctions": true}', 70),
    ("patriarches", "Patriarches", "Les membres actifs détenant la fonction Patriarche (responsables de tribu), fonction active et confirmée, dédupliqués.", "responsabilite", "fonction", '{"fonction_cles": ["patriarche"]}', 80),
    ("liste", "Liste d'adresses e-mail (groupe ad hoc)", "Une liste explicite d'adresses e-mail saisie pour cette activité.", "adhoc", "liste", "{}", 90),
]


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE cible_activite (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            code text NOT NULL UNIQUE,
            libelle text NOT NULL,
            description text,
            categorie text NOT NULL DEFAULT 'audience',
            type_regle text NOT NULL,
            parametres jsonb NOT NULL DEFAULT '{}'::jsonb,
            ordre int NOT NULL DEFAULT 0,
            statut text NOT NULL DEFAULT 'actif',
            cree_le timestamptz DEFAULT now(),
            cree_par uuid,
            maj_le timestamptz DEFAULT now(),
            maj_par uuid,
            CONSTRAINT cible_activite_regle_chk CHECK (type_regle IN ('tous', 'unite', 'fonction', 'attribut', 'liste')),
            CONSTRAINT cible_activite_statut_chk CHECK (statut IN ('actif', 'inactif', 'archive'))
        )
        """
    )
    op.execute("ALTER TABLE cible_activite ADD CONSTRAINT fk_cible_activite_cree_par FOREIGN KEY (cree_par) REFERENCES utilisateur(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE cible_activite ADD CONSTRAINT fk_cible_activite_maj_par FOREIGN KEY (maj_par) REFERENCES utilisateur(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE cible_activite ENABLE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY cible_activite_select ON cible_activite FOR SELECT USING (adsum_current_role() = ANY({_LECTURE}))")
    op.execute(f"CREATE POLICY cible_activite_write ON cible_activite FOR ALL USING (adsum_current_role() = ANY({_ECRITURE})) WITH CHECK (adsum_current_role() = ANY({_ECRITURE}))")

    for code, libelle, description, categorie, type_regle, parametres, ordre in _SEED:
        op.execute(
            "INSERT INTO cible_activite (code, libelle, description, categorie, type_regle, parametres, ordre) "
            "SELECT %s, %s, %s, %s, %s, %s::jsonb, %s WHERE NOT EXISTS (SELECT 1 FROM cible_activite WHERE code = %s)",
            (code, libelle, description, categorie, type_regle, parametres, ordre, code),
        )

    # Data-driven integrity: the allowed cible_type values now live in the referentiel.
    op.execute("ALTER TABLE evenement DROP CONSTRAINT IF EXISTS evenement_cible_type_chk")
    op.execute("ALTER TABLE evenement DROP CONSTRAINT IF EXISTS evenement_cible_pair_chk")
    op.execute("ALTER TABLE evenement ADD CONSTRAINT fk_evenement_cible_type FOREIGN KEY (cible_type) REFERENCES cible_activite(code)")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION evenement_cible_coherence() RETURNS trigger AS $$
        DECLARE regle text;
        BEGIN
            SELECT type_regle INTO regle FROM cible_activite WHERE code = NEW.cible_type;
            IF regle IS NULL THEN
                RAISE EXCEPTION 'cible_type inconnu: %', NEW.cible_type;
            END IF;
            IF regle = 'unite' AND NEW.cible_id IS NULL THEN
                RAISE EXCEPTION 'cible % : une unite (cible_id) est requise', NEW.cible_type;
            END IF;
            IF regle <> 'unite' AND NEW.cible_id IS NOT NULL THEN
                RAISE EXCEPTION 'cible % : cible_id doit rester vide', NEW.cible_type;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER trg_evenement_cible_coherence BEFORE INSERT OR UPDATE OF cible_type, cible_id ON evenement "
        "FOR EACH ROW EXECUTE FUNCTION evenement_cible_coherence()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_evenement_cible_coherence ON evenement")
    op.execute("DROP FUNCTION IF EXISTS evenement_cible_coherence()")
    op.execute("ALTER TABLE evenement DROP CONSTRAINT IF EXISTS fk_evenement_cible_type")
    op.execute(
        "ALTER TABLE evenement ADD CONSTRAINT evenement_cible_type_chk CHECK "
        "(cible_type = ANY (ARRAY['general', 'coordination', 'commission', 'intendance', 'tribu', 'bergers', 'responsables', 'liste']))"
    )
    op.execute(
        "ALTER TABLE evenement ADD CONSTRAINT evenement_cible_pair_chk CHECK "
        "((cible_type IN ('general', 'bergers', 'responsables', 'liste') AND cible_id IS NULL) "
        "OR (cible_type IN ('coordination', 'commission', 'intendance', 'tribu') AND cible_id IS NOT NULL))"
    )
    op.execute("DROP TABLE IF EXISTS cible_activite")
