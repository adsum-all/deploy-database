# ruff: noqa: E501 - migrations carry long SQL lines
"""Database-level guarantee: a group tied to an application requires active visibility.

Closes the two-step invariant at the source. A ``membre_groupe`` row whose
``application_code`` is not NULL may exist only while the member holds an active
``membre_application_acces`` for that same application. Enforced by a BEFORE INSERT OR
UPDATE trigger, so a right can never be created (even under a concurrent revocation race)
without the visibility that justifies it. The trigger does NOT fire on DELETE, so the
revocation cascade (which deletes those rows) is unaffected. Global group assignments
(application_code IS NULL, from « Acces & groupes ») are exempt.

Revision ID: 0138_membre_groupe_acces_requis
Revises: 0137_app_mobile_membre
Create Date: 2026-07-13
"""
from __future__ import annotations

from alembic import op

revision = "0138_membre_groupe_acces_requis"
down_revision = "0137_app_mobile_membre"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION adsum_membre_groupe_acces_requis() RETURNS trigger AS $$
        BEGIN
            IF NEW.application_code IS NOT NULL THEN
                IF NOT EXISTS (
                    SELECT 1 FROM membre_application_acces m
                    WHERE m.membre_id = NEW.membre_id
                      AND m.application_code = NEW.application_code
                      AND m.actif = true
                ) THEN
                    RAISE EXCEPTION 'un droit lie a l''application % exige une visibilite active pour le membre %', NEW.application_code, NEW.membre_id
                        USING ERRCODE = 'check_violation';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS trg_membre_groupe_acces_requis ON membre_groupe")
    op.execute(
        "CREATE TRIGGER trg_membre_groupe_acces_requis "
        "BEFORE INSERT OR UPDATE ON membre_groupe "
        "FOR EACH ROW EXECUTE FUNCTION adsum_membre_groupe_acces_requis()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_membre_groupe_acces_requis ON membre_groupe")
    op.execute("DROP FUNCTION IF EXISTS adsum_membre_groupe_acces_requis()")
