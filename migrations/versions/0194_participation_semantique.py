# ruff: noqa: E501 - migrations carry long SQL lines
"""Say precisely what a participation record means.

Until now a row said `present`, `partiel` or `absent`, with a modality bolted on the
side. Three different facts were wearing the same word. A person scanned at the door
and a person who typed "présent" into a form produced identical rows. "Partiel" was
offered for on-site attendance, where it means nothing: you were in the room or you
were not. And an absence carried no reason, so nobody could tell an excused absence
from a silent one, because neither existed.

This migration gives each fact its own column, and adds nothing destructive: every
existing column keeps its meaning and its data. The old `statut` stays authoritative
for everything already written; the new columns describe the same rows more precisely
and are back-filled from what can be deduced with certainty.

Four decisions worth stating.

Confidence is recorded, not inferred at read time. A scan is proof, a member's word is
a declaration, and a measured online duration is something else again. Every screen
that shows a figure needs to know which of the three it is holding, and deriving it
from `source` at each call site is how two screens end up disagreeing.

Partial belongs to online attendance only. On site you were there or you were not.
The 109 rows currently saying "partiel en présentiel" cannot be converted: nobody
knows whether the person meant they arrived late or that they followed intermittently
from a phone. They are flagged `legacy_ambigu` and excluded from the rates rather than
guessed at. Rewriting them would put an answer in somebody's mouth.

An absence reason is never a decision. The member says why; a responsible person
decides whether it is excused. Those are two columns, two moments and two actors, and
collapsing them is precisely how a member ends up excusing themselves.

The catalogue of reasons is a table, not an enum. An organisation adds a reason
without a migration, and a reason that stops being used is deactivated rather than
deleted, so the absences that cited it keep their meaning.

Revision ID: 0194_participation_semantique
Revises: 0193_direction_rapport_planifie
Create Date: 2026-08-08
"""
from __future__ import annotations

from alembic import op

revision = "0194_participation_semantique"
down_revision = "0193_direction_rapport_planifie"
branch_labels = None
depends_on = None

#: Who may decide that an absence is excused. Never the member.
_DECIDEURS = "ARRAY['super_admin', 'admin', 'gestionnaire', 'direction']::text[]"


def upgrade() -> None:
    # --- The catalogue of absence reasons ---------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS motif_absence (
            code text PRIMARY KEY,
            libelle text NOT NULL,
            libelle_en text,
            ordre integer NOT NULL DEFAULT 100,
            actif boolean NOT NULL DEFAULT true,
            commentaire_requis boolean NOT NULL DEFAULT false,
            cree_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "COMMENT ON TABLE motif_absence IS "
        "'Catalogue administrable des raisons d''absence proposées au membre. "
        "Une raison retirée est désactivée et non supprimée, pour que les absences "
        "qui la citent gardent leur sens.'"
    )
    # Seeded with the list the organisation asked for. WHERE NOT EXISTS rather than a
    # plain insert, so re-running this migration cannot duplicate the catalogue.
    for code, libelle, en, ordre, commentaire in (
        ("empechement_personnel", "Empêchement personnel", "Personal impediment", 10, False),
        ("empechement_professionnel", "Empêchement professionnel", "Work impediment", 20, False),
        ("sante", "Problème de santé", "Health issue", 30, False),
        ("famille", "Contrainte familiale", "Family constraint", 40, False),
        ("transport", "Difficulté de transport", "Travel difficulty", 50, False),
        ("technique", "Difficulté technique ou de connexion", "Technical or connection issue", 60, False),
        ("chevauchement", "Chevauchement avec une autre activité", "Clash with another activity", 70, False),
        ("absence_prevue", "Absence prévue", "Planned absence", 80, False),
        ("autre", "Autre raison", "Other reason", 90, True),
        ("non_precise", "Je ne souhaite pas préciser", "I prefer not to say", 100, False),
    ):
        op.execute(
            "INSERT INTO motif_absence (code, libelle, libelle_en, ordre, commentaire_requis) "
            f"SELECT '{code}', '{libelle}', '{en}', {ordre}, {str(commentaire).lower()} "
            f"WHERE NOT EXISTS (SELECT 1 FROM motif_absence WHERE code = '{code}')"
        )

    op.execute("ALTER TABLE motif_absence ENABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS motif_absence_lecture ON motif_absence")
    op.execute(
        "CREATE POLICY motif_absence_lecture ON motif_absence FOR SELECT "
        "USING (COALESCE(adsum_current_role(), '') <> '')"
    )
    op.execute("DROP POLICY IF EXISTS motif_absence_ecriture ON motif_absence")
    op.execute(
        "CREATE POLICY motif_absence_ecriture ON motif_absence FOR ALL "
        "USING (COALESCE(adsum_current_role(), '') = ANY(ARRAY['super_admin', 'admin']::text[])) "
        "WITH CHECK (COALESCE(adsum_current_role(), '') = ANY(ARRAY['super_admin', 'admin']::text[]))"
    )
    op.execute("REVOKE ALL ON motif_absence FROM anon")

    # --- Participation: one column per fact -------------------------------
    op.execute("ALTER TABLE participation ADD COLUMN IF NOT EXISTS mode_suivi text")
    op.execute("ALTER TABLE participation ADD COLUMN IF NOT EXISTS niveau_en_ligne text")
    op.execute("ALTER TABLE participation ADD COLUMN IF NOT EXISTS confiance text")
    op.execute("ALTER TABLE participation ADD COLUMN IF NOT EXISTS legacy_ambigu boolean NOT NULL DEFAULT false")
    op.execute("ALTER TABLE participation ADD COLUMN IF NOT EXISTS absence_motif text")
    op.execute("ALTER TABLE participation ADD COLUMN IF NOT EXISTS absence_commentaire text")
    op.execute("ALTER TABLE participation ADD COLUMN IF NOT EXISTS absence_qualification text NOT NULL DEFAULT 'sans_objet'")
    op.execute("ALTER TABLE participation ADD COLUMN IF NOT EXISTS qualifie_par uuid")
    op.execute("ALTER TABLE participation ADD COLUMN IF NOT EXISTS qualifie_le timestamptz")
    op.execute("ALTER TABLE participation ADD COLUMN IF NOT EXISTS qualification_commentaire text")

    op.execute(
        "COMMENT ON COLUMN participation.mode_suivi IS "
        "'Comment la personne a suivi : presentiel, en_ligne, ou aucun si elle n''a pas suivi.'"
    )
    op.execute(
        "COMMENT ON COLUMN participation.niveau_en_ligne IS "
        "'Uniquement pour un suivi en ligne : complet ou partiel. Le presentiel n''a pas "
        "de niveau, on y est ou on n''y est pas.'"
    )
    op.execute(
        "COMMENT ON COLUMN participation.confiance IS "
        "'Ce qui fonde l''enregistrement : prouvee (scan au point de controle), "
        "mesuree (duree relevee par la plateforme), declaree (parole du membre), "
        "administrative (correction par un responsable).'"
    )
    op.execute(
        "COMMENT ON COLUMN participation.legacy_ambigu IS "
        "'Ligne ecrite sous l''ancien modele et non convertible avec certitude. "
        "Conservee telle quelle, exclue des taux, jamais reecrite.'"
    )
    op.execute(
        "COMMENT ON COLUMN participation.absence_qualification IS "
        "'sans_objet quand la personne a suivi. Sinon en_attente, excusee ou "
        "non_excusee. Seul un responsable habilite peut sortir de en_attente.'"
    )

    op.execute("ALTER TABLE participation DROP CONSTRAINT IF EXISTS participation_mode_suivi_check")
    op.execute(
        "ALTER TABLE participation ADD CONSTRAINT participation_mode_suivi_check "
        "CHECK (mode_suivi IS NULL OR mode_suivi IN ('presentiel', 'en_ligne', 'aucun'))"
    )
    op.execute("ALTER TABLE participation DROP CONSTRAINT IF EXISTS participation_niveau_en_ligne_check")
    op.execute(
        "ALTER TABLE participation ADD CONSTRAINT participation_niveau_en_ligne_check "
        "CHECK (niveau_en_ligne IS NULL OR niveau_en_ligne IN ('complet', 'partiel'))"
    )
    op.execute("ALTER TABLE participation DROP CONSTRAINT IF EXISTS participation_confiance_check")
    op.execute(
        "ALTER TABLE participation ADD CONSTRAINT participation_confiance_check "
        "CHECK (confiance IS NULL OR confiance IN ('prouvee', 'mesuree', 'declaree', 'administrative'))"
    )
    op.execute("ALTER TABLE participation DROP CONSTRAINT IF EXISTS participation_qualification_check")
    op.execute(
        "ALTER TABLE participation ADD CONSTRAINT participation_qualification_check "
        "CHECK (absence_qualification IN ('sans_objet', 'en_attente', 'excusee', 'non_excusee'))"
    )
    # A decision without a decider is not a decision. The constraint says so, rather
    # than trusting every future write path to remember.
    op.execute("ALTER TABLE participation DROP CONSTRAINT IF EXISTS participation_decision_tracee")
    op.execute(
        "ALTER TABLE participation ADD CONSTRAINT participation_decision_tracee "
        "CHECK (absence_qualification IN ('sans_objet', 'en_attente') "
        "OR (qualifie_par IS NOT NULL AND qualifie_le IS NOT NULL))"
    )
    op.execute("ALTER TABLE participation DROP CONSTRAINT IF EXISTS participation_qualifie_par_fkey")
    op.execute(
        "ALTER TABLE participation ADD CONSTRAINT participation_qualifie_par_fkey "
        "FOREIGN KEY (qualifie_par) REFERENCES utilisateur (id) ON DELETE SET NULL"
    )
    op.execute("ALTER TABLE participation DROP CONSTRAINT IF EXISTS participation_absence_motif_fkey")
    op.execute(
        "ALTER TABLE participation ADD CONSTRAINT participation_absence_motif_fkey "
        "FOREIGN KEY (absence_motif) REFERENCES motif_absence (code) ON DELETE SET NULL"
    )

    # A responsible person correcting a record, and an online session recorded by the
    # platform, are neither a scan nor a member declaration. The vocabulary has to
    # admit them or those writes cannot be told apart afterwards.
    op.execute("ALTER TABLE participation DROP CONSTRAINT IF EXISTS participation_source_check")
    op.execute(
        "ALTER TABLE participation ADD CONSTRAINT participation_source_check "
        "CHECK (source IN ('scan', 'declaration', 'session_en_ligne', 'decision_responsable', 'import'))"
    )

    # --- Back-fill: only what can be deduced with certainty ---------------
    # A scan is on-site and proven, whatever the old row said.
    op.execute(
        "UPDATE participation SET mode_suivi = 'presentiel', confiance = 'prouvee', "
        "modalite = 'presentiel' "
        "WHERE source = 'scan' AND mode_suivi IS NULL"
    )
    # A declared presence online, and a declared presence on site, are unambiguous.
    op.execute(
        "UPDATE participation SET mode_suivi = 'en_ligne', niveau_en_ligne = 'complet', "
        "confiance = 'declaree' "
        "WHERE source <> 'scan' AND statut = 'present' AND modalite = 'en_ligne' AND mode_suivi IS NULL"
    )
    op.execute(
        "UPDATE participation SET mode_suivi = 'presentiel', confiance = 'declaree' "
        "WHERE source <> 'scan' AND statut = 'present' AND modalite = 'presentiel' AND mode_suivi IS NULL"
    )
    # Partial online is exactly what the new model calls partial online.
    op.execute(
        "UPDATE participation SET mode_suivi = 'en_ligne', niveau_en_ligne = 'partiel', "
        "confiance = 'declaree' "
        "WHERE statut = 'partiel' AND modalite = 'en_ligne' AND mode_suivi IS NULL"
    )
    # Partial on site cannot be converted: nobody knows whether the person arrived
    # late or followed intermittently. Flagged, kept, excluded from the rates.
    op.execute(
        "UPDATE participation SET legacy_ambigu = true, confiance = 'declaree' "
        "WHERE statut = 'partiel' AND modalite = 'presentiel' AND NOT legacy_ambigu"
    )
    # An absence has no mode and no level, and starts its life awaiting nothing:
    # a reason has not been given, so there is no decision to await.
    op.execute(
        "UPDATE participation SET mode_suivi = 'aucun', confiance = 'declaree' "
        "WHERE statut = 'absent' AND mode_suivi IS NULL"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS participation_absence_a_qualifier "
        "ON participation (absence_qualification, evenement_id) "
        "WHERE absence_qualification = 'en_attente'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS participation_mode_suivi_idx "
        "ON participation (mode_suivi, niveau_en_ligne) WHERE NOT legacy_ambigu"
    )

    # --- Questionnaire: draft, publication, version -----------------------
    op.execute("ALTER TABLE questionnaire ADD COLUMN IF NOT EXISTS statut text NOT NULL DEFAULT 'publie'")
    op.execute("ALTER TABLE questionnaire ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1")
    op.execute("ALTER TABLE questionnaire ADD COLUMN IF NOT EXISTS publie_le timestamptz")
    op.execute("ALTER TABLE questionnaire ADD COLUMN IF NOT EXISTS publie_par uuid")
    op.execute("ALTER TABLE questionnaire ADD COLUMN IF NOT EXISTS maj_le timestamptz NOT NULL DEFAULT now()")
    op.execute("ALTER TABLE questionnaire DROP CONSTRAINT IF EXISTS questionnaire_statut_check")
    op.execute(
        "ALTER TABLE questionnaire ADD CONSTRAINT questionnaire_statut_check "
        "CHECK (statut IN ('brouillon', 'publie', 'archive'))"
    )
    # Existing questionnaires default to published: they already are, from the
    # members' point of view, and silently unpublishing them would remove a form
    # people are in the middle of answering.
    op.execute("UPDATE questionnaire SET publie_le = cree_le WHERE statut = 'publie' AND publie_le IS NULL")

    # A question that already carries answers must not be deleted silently. The
    # column records how many were counted at the last save, so the interface can
    # warn instead of destroying.
    op.execute("ALTER TABLE question ADD COLUMN IF NOT EXISTS archivee boolean NOT NULL DEFAULT false")
    op.execute(
        "COMMENT ON COLUMN question.archivee IS "
        "'Question retiree du formulaire mais conservee, parce que des reponses la "
        "citent par son identifiant. La supprimer rendrait ces reponses illisibles.'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS participation_mode_suivi_idx")
    op.execute("DROP INDEX IF EXISTS participation_absence_a_qualifier")
    for c in (
        "participation_decision_tracee", "participation_qualification_check",
        "participation_confiance_check", "participation_niveau_en_ligne_check",
        "participation_mode_suivi_check", "participation_qualifie_par_fkey",
        "participation_absence_motif_fkey",
    ):
        op.execute(f"ALTER TABLE participation DROP CONSTRAINT IF EXISTS {c}")
    op.execute("ALTER TABLE participation DROP CONSTRAINT IF EXISTS participation_source_check")
    op.execute(
        "ALTER TABLE participation ADD CONSTRAINT participation_source_check "
        "CHECK (source IN ('scan', 'declaration'))"
    )
    for col in (
        "mode_suivi", "niveau_en_ligne", "confiance", "legacy_ambigu", "absence_motif",
        "absence_commentaire", "absence_qualification", "qualifie_par", "qualifie_le",
        "qualification_commentaire",
    ):
        op.execute(f"ALTER TABLE participation DROP COLUMN IF EXISTS {col}")
    op.execute("ALTER TABLE question DROP COLUMN IF EXISTS archivee")
    op.execute("ALTER TABLE questionnaire DROP CONSTRAINT IF EXISTS questionnaire_statut_check")
    for col in ("statut", "version", "publie_le", "publie_par", "maj_le"):
        op.execute(f"ALTER TABLE questionnaire DROP COLUMN IF EXISTS {col}")
    op.execute("DROP TABLE IF EXISTS motif_absence")
