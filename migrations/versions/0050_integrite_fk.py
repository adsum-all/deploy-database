# ruff: noqa: E501 - migrations carry long SQL and seeded text lines
"""Referential-integrity hardening and attestation-to-ticket unification.

1. Every reference-shaped column that lacked a foreign key gets one (audited on
   the live database: zero orphan rows on all of them, so validation is safe).
   ON DELETE SET NULL for tracing pointers (who validated/published/handles),
   so the RGPD erasure of a user account never breaks history rows; CASCADE for
   member-owned child data. The audit journal's objet_id stays without FK by
   design: it is polymorphic (points at any entity type).
2. The hand-signed attestation task becomes a tracked request: a demande ticket
   is linked (attestation_manuelle.demande_id), the 'document' type is allowed,
   and existing attestations are backfilled with their ticket and timeline so
   the member and the back office finally see them in the tracking pages.

Revision ID: 0050_integrite_fk
Revises: 0049_demande_suivi
Create Date: 2026-07-03
"""
from __future__ import annotations

from alembic import op

revision = "0050_integrite_fk"
down_revision = "0049_demande_suivi"
branch_labels = None
depends_on = None

# (table, column, target_table, on_delete)
_FKS = [
    ("attestation_manuelle", "document_id", "document", "SET NULL"),
    ("attestation_manuelle", "signature_id", "signature_engagement", "SET NULL"),
    ("attestation_manuelle", "valide_par", "utilisateur", "SET NULL"),
    ("attestation_manuelle", "demande_id", "demande", "SET NULL"),
    ("collab_carte", "cree_par", "utilisateur", "SET NULL"),
    ("collab_tableau", "cree_par", "utilisateur", "SET NULL"),
    ("collab_commentaire", "auteur_id", "utilisateur", "SET NULL"),
    ("collab_version", "auteur_id", "utilisateur", "SET NULL"),
    ("correction_historique", "modifie_par", "membre", "SET NULL"),
    ("demande", "pris_en_charge_par", "utilisateur", "SET NULL"),
    ("demande_message", "document_id", "document", "SET NULL"),
    ("detection_doublon", "decide_par", "utilisateur", "SET NULL"),
    ("document_consentement", "publie_par", "utilisateur", "SET NULL"),
    ("engagement", "signature_id", "signature_engagement", "SET NULL"),
    ("evenement", "serie_id", "evenement", "SET NULL"),
    ("fonction_honorifique", "maj_par", "utilisateur", "SET NULL"),
    ("integration_config", "maj_par", "utilisateur", "SET NULL"),
    ("membre", "decision_par", "utilisateur", "SET NULL"),
    ("modele_message", "maj_par", "utilisateur", "SET NULL"),
    ("modification_membre", "decide_par", "utilisateur", "SET NULL"),
    ("notification_echec", "membre_id", "membre", "CASCADE"),
    ("pays_signature", "maj_par", "utilisateur", "SET NULL"),
]


def upgrade() -> None:
    # 1. The attestation task links to its tracking ticket.
    op.execute("ALTER TABLE attestation_manuelle ADD COLUMN IF NOT EXISTS demande_id uuid")

    # 2. Allow the 'document' request type (document to return or transmit).
    op.execute("ALTER TABLE demande DROP CONSTRAINT IF EXISTS demande_type_chk")
    op.execute(
        "ALTER TABLE demande ADD CONSTRAINT demande_type_chk CHECK ("
        "type IN ('modification_info', 'question', 'reclamation', 'autre', 'document'))"
    )

    # 3. Foreign keys (idempotent; every column audited orphan-free beforehand).
    for table, col, target, action in _FKS:
        name = f"fk_{table}_{col}"
        op.execute(
            f"""
            DO $$ BEGIN
              IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = '{name}') THEN
                ALTER TABLE {table} ADD CONSTRAINT {name}
                  FOREIGN KEY ({col}) REFERENCES {target}(id) ON DELETE {action};
              END IF;
            END $$
            """
        )

    # 4. Backfill: one tracking ticket per existing attestation, plus timeline.
    op.execute(
        """
        WITH a AS (
            SELECT id, membre_id, statut, ouverte_le, valide_le
            FROM attestation_manuelle WHERE demande_id IS NULL
        ), ins AS (
            INSERT INTO demande (membre_id, type, sujet, categorie, sous_categorie, statut, motif_cloture, clos_le, cree_le)
            SELECT membre_id, 'document', 'Attestation signée à retourner', 'documents', 'attestation_retour',
                   CASE statut
                       WHEN 'accepted' THEN 'resolue'
                       WHEN 'invalidated' THEN 'refusee'
                       WHEN 'under_review' THEN 'en_validation'
                       ELSE 'attente_membre'
                   END,
                   CASE statut WHEN 'accepted' THEN 'Attestation validée' WHEN 'invalidated' THEN 'Attestation invalidée' END,
                   CASE WHEN statut IN ('accepted', 'invalidated') THEN valide_le END,
                   coalesce(ouverte_le, now())
            FROM a
            RETURNING id, membre_id
        )
        UPDATE attestation_manuelle am SET demande_id = ins.id
        FROM ins WHERE am.membre_id = ins.membre_id AND am.demande_id IS NULL
        """
    )
    op.execute(
        """
        INSERT INTO demande_message (demande_id, auteur_type, auteur_nom, corps, cree_le)
        SELECT am.demande_id, 'systeme', 'ADSUM',
               'Votre pays exige une attestation signée à la main. Imprimez le document depuis Ma carte, signez-le, puis renvoyez la version scannée.',
               coalesce(am.ouverte_le, now())
        FROM attestation_manuelle am
        WHERE am.demande_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM demande_message dm WHERE dm.demande_id = am.demande_id)
        """
    )
    op.execute(
        """
        INSERT INTO demande_message (demande_id, auteur_type, auteur_nom, corps, cree_le)
        SELECT am.demande_id, 'systeme', 'ADSUM',
               'Document signé transmis. En cours de vérification par l''administration.',
               coalesce(am.soumise_le, now())
        FROM attestation_manuelle am
        WHERE am.demande_id IS NOT NULL AND am.statut = 'under_review'
          AND NOT EXISTS (
            SELECT 1 FROM demande_message dm
            WHERE dm.demande_id = am.demande_id AND dm.corps LIKE 'Document signé transmis%'
          )
        """
    )
    # The transmitted scan itself must be openable from the ticket conversation.
    op.execute(
        """
        INSERT INTO demande_message (demande_id, auteur_type, auteur_nom, corps, document_id, cree_le)
        SELECT am.demande_id, 'membre',
               (SELECT trim(coalesce(m.prenoms, '') || ' ' || coalesce(m.nom, '')) FROM membre m WHERE m.id = am.membre_id),
               'Attestation signée transmise.', am.document_id, coalesce(am.soumise_le, now())
        FROM attestation_manuelle am
        WHERE am.demande_id IS NOT NULL AND am.document_id IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM demande_message dm
            WHERE dm.demande_id = am.demande_id AND dm.document_id IS NOT NULL
          )
        """
    )


def downgrade() -> None:
    for table, col, _, _ in _FKS:
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS fk_{table}_{col}")
    op.execute("ALTER TABLE attestation_manuelle DROP COLUMN IF EXISTS demande_id")
    op.execute("ALTER TABLE demande DROP CONSTRAINT IF EXISTS demande_type_chk")
    op.execute(
        "ALTER TABLE demande ADD CONSTRAINT demande_type_chk CHECK ("
        "type IN ('modification_info', 'question', 'reclamation', 'autre'))"
    )
