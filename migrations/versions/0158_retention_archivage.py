# ruff: noqa: E501 - migrations carry long SQL lines
"""Retention and archiving for communications (Informations, Notifications, Telegram).

Adds only what a durable, auditable retention policy needs, and NOTHING that could
silently erase business data:

- ``information.protege`` / ``information.institutionnelle``: an Information flagged
  protected or institutional is never auto-archived nor auto-deleted.
- ``retention_journal``: an append-only audit trail of every archive, delete, skip
  or protected decision, with the rule applied and the actor.
- Default retention settings in ``integration_config`` (key/value): archive after
  24 months, deletion OFF by default (``retention_auto_suppression`` = false), so no
  final deletion ever happens without an explicit administrative opt-in.

Revision ID: 0158_retention_archivage
Revises: 0157_notification_centre
Create Date: 2026-07-19
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0158_retention_archivage"
down_revision = "0157_notification_centre"
branch_labels = None
depends_on = None

_DEFAULTS = [
    ("retention_info_archive_mois", "24"),
    ("retention_info_suppression_mois", "0"),
    ("retention_notif_lues_jours", "90"),
    ("retention_notif_nonlues_jours", "180"),
    ("retention_notif_suppression_mois", "24"),
    ("retention_auto_suppression", "false"),
    ("telegram_retention_jours", "14"),
]


def upgrade() -> None:
    op.execute("ALTER TABLE information ADD COLUMN IF NOT EXISTS protege boolean NOT NULL DEFAULT false")
    op.execute("ALTER TABLE information ADD COLUMN IF NOT EXISTS institutionnelle boolean NOT NULL DEFAULT false")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS retention_journal (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            type_element text NOT NULL,
            element_id uuid,
            titre text,
            element_cree_le timestamptz,
            archive_le timestamptz,
            supprime_le timestamptz,
            regle text,
            acteur text,
            destinataires integer,
            a_media boolean,
            resultat text NOT NULL,
            motif_exclusion text,
            rapport_ref text,
            execute_le timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_retention_journal_execute ON retention_journal (execute_le DESC)")
    op.execute("ALTER TABLE retention_journal ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY retention_journal_select ON retention_journal FOR SELECT "
        "USING (adsum_current_role() = ANY(ARRAY['super_admin','admin','gestionnaire','direction']::text[]))"
    )
    op.execute(
        "CREATE POLICY retention_journal_write ON retention_journal FOR ALL "
        "USING (adsum_current_role() = ANY(ARRAY['super_admin','admin']::text[])) "
        "WITH CHECK (adsum_current_role() = ANY(ARRAY['super_admin','admin']::text[]))"
    )

    bind = op.get_bind()
    for cle, valeur in _DEFAULTS:
        bind.execute(
            sa.text("INSERT INTO integration_config (cle, valeur) VALUES (:cle, :valeur) ON CONFLICT (cle) DO NOTHING"),
            {"cle": cle, "valeur": valeur},
        )
    # telegram_retention_jours previously defaulted to 90 in code only; if a row was
    # never created it is seeded to 14 above. An existing row is left untouched.


def downgrade() -> None:
    op.execute("DELETE FROM integration_config WHERE cle = ANY(ARRAY['retention_info_archive_mois','retention_info_suppression_mois','retention_notif_lues_jours','retention_notif_nonlues_jours','retention_notif_suppression_mois','retention_auto_suppression']::text[])")
    op.execute("DROP TABLE IF EXISTS retention_journal")
    op.execute("ALTER TABLE information DROP COLUMN IF EXISTS institutionnelle")
    op.execute("ALTER TABLE information DROP COLUMN IF EXISTS protege")
