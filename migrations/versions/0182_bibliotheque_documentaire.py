# ruff: noqa: E501 - migrations carry long SQL lines
"""A library for the institution's own documents, with real versions.

Consent texts were the only institutional writing the platform held, and they lived
under one flag: ``actif``. Publishing a new version silently hid the previous one,
which nobody could read back, so a member who signed version 2 had no way to see what
version 2 actually said. For a document somebody signs, that is the whole point.

This library holds statutes, rules, charters and notes as documents with a life of
their own: a draft that is not visible, a published version that is, an archive that
stays readable. Each version keeps its text and a fingerprint of it, so what was
signed can always be shown again exactly as it was.

Bilingual from the start, because the consent texts already are and a library that
was not would push the organisation back to one language.

A version carries either its text or an attached file, or both: a charter is written
here, a signed statute arrives as a PDF, and forcing one shape on both would mean
storing a scanned document as an empty body.

Revision ID: 0182_bibliotheque_documentaire
Revises: 0181_supervision_tribus
Create Date: 2026-07-29
"""
from __future__ import annotations

from alembic import op

revision = "0182_bibliotheque_documentaire"
down_revision = "0181_supervision_tribus"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS document_institutionnel (
            id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            cle          text NOT NULL UNIQUE,
            categorie    text NOT NULL DEFAULT 'reglement',
            titre        text NOT NULL,
            titre_en     text,
            description  text,
            -- Who may read it once published. 'gouvernance' keeps a document inside
            -- the back office; 'public' allows the site to serve it unauthenticated.
            visibilite   text NOT NULL DEFAULT 'membres',
            statut       text NOT NULL DEFAULT 'brouillon',
            ordre        int NOT NULL DEFAULT 100,
            cree_le      timestamptz NOT NULL DEFAULT now(),
            cree_par     uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            maj_le       timestamptz,
            maj_par      uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            CONSTRAINT document_institutionnel_statut CHECK (statut IN ('brouillon', 'publie', 'archive')),
            CONSTRAINT document_institutionnel_visibilite CHECK (visibilite IN ('public', 'membres', 'gouvernance')),
            CONSTRAINT document_institutionnel_categorie CHECK (
                categorie IN ('statuts', 'reglement', 'charte', 'procedure', 'note', 'formulaire')
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS document_institutionnel_version (
            id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id    uuid NOT NULL REFERENCES document_institutionnel(id) ON DELETE CASCADE,
            version        int NOT NULL,
            contenu        text,
            contenu_en     text,
            -- An attached file lives in the private bucket; the row keeps its path.
            bucket         text,
            chemin         text,
            nom_fichier    text,
            mime           text,
            taille         bigint,
            -- Fingerprint of exactly what was published, so a signature can be shown
            -- against the text it was given, not against whatever the text became.
            empreinte      text,
            notes          text,
            publie_le      timestamptz,
            publie_par     uuid REFERENCES utilisateur(id) ON DELETE SET NULL,
            cree_le        timestamptz NOT NULL DEFAULT now(),
            UNIQUE (document_id, version)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS document_institutionnel_version_doc_idx "
        "ON document_institutionnel_version (document_id, version DESC)"
    )
    op.execute("ALTER TABLE document_institutionnel ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE document_institutionnel_version ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON document_institutionnel FROM anon, authenticated")
    op.execute("REVOKE ALL ON document_institutionnel_version FROM anon, authenticated")

    # An engagement named its document by free text, so nothing tied a signature to
    # the exact wording it approved. The reference is added without dropping the old
    # columns: they carry the history of the signatures already collected.
    op.execute(
        "ALTER TABLE engagement ADD COLUMN IF NOT EXISTS document_consentement_id uuid"
    )
    op.execute("ALTER TABLE engagement DROP CONSTRAINT IF EXISTS engagement_document_consentement_fk")
    op.execute(
        "ALTER TABLE engagement ADD CONSTRAINT engagement_document_consentement_fk "
        "FOREIGN KEY (document_consentement_id) REFERENCES document_consentement(id) ON DELETE SET NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS engagement_document_consentement_idx "
        "ON engagement (document_consentement_id)"
    )
    # Attach the signatures already collected to the wording they matched, by key and
    # version. Anything that finds no match keeps its free-text reference, which is
    # honest: inventing a link would be worse than admitting the gap.
    op.execute(
        """
        UPDATE engagement e
           SET document_consentement_id = d.id
          FROM document_consentement d
         WHERE e.document_consentement_id IS NULL
           AND d.cle = e.type
           AND d.version::text = e.version
        """
    )

    op.execute(
        """
        INSERT INTO permission (cle, domaine, libelle, description, risque, portee, systeme)
        VALUES ('documents.bibliotheque', 'documents', 'Documents - bibliothèque institutionnelle',
                'Rédiger, versionner, publier et archiver les documents institutionnels (statuts, règlements, chartes).',
                'moyen', 'global', false)
        ON CONFLICT (cle) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO permission_application (permission, application_code)
        SELECT 'documents.bibliotheque', a.code
          FROM application a
         WHERE a.code IN ('back-office', 'direction')
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM permission_application WHERE permission = 'documents.bibliotheque'")
    op.execute("DELETE FROM permission WHERE cle = 'documents.bibliotheque'")
    op.execute("ALTER TABLE engagement DROP CONSTRAINT IF EXISTS engagement_document_consentement_fk")
    op.execute("ALTER TABLE engagement DROP COLUMN IF EXISTS document_consentement_id")
    op.execute("DROP TABLE IF EXISTS document_institutionnel_version")
    op.execute("DROP TABLE IF EXISTS document_institutionnel")
