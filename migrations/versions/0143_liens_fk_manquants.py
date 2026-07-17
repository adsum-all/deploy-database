# ruff: noqa: E501 - migrations carry long SQL lines
"""Enforce the last internal references with real foreign keys.

Three columns referenced an internal entity but had no FK constraint. The data is already
consistent (audited: zero orphan rows), so we add the constraints to guarantee the links can
never break in the future. ON DELETE SET NULL: deleting the referenced row nulls the pointer
without destroying the child (an event picture keeps existing if its author is removed, the
patriarche history keeps its record, the Telegram ingest ledger keeps its row).

Polymorphic columns (audit.objet_id, evenement.cible_id, membre_groupe.portee_id,
consultation.scope_id, notification_log.ref_id) and external identifiers (Telegram chat/
message/file ids, device id) intentionally have no FK: they do not reference a single table.

Revision ID: 0143_liens_fk_manquants
Revises: 0142_telegram_relink_all
Create Date: 2026-07-16
"""
from __future__ import annotations

from alembic import op

revision = "0143_liens_fk_manquants"
down_revision = "0142_telegram_relink_all"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE evenement_piece ADD CONSTRAINT fk_evenement_piece_cree_par FOREIGN KEY (cree_par) REFERENCES utilisateur(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE tribu_patriarche_historique ADD CONSTRAINT fk_tribu_patriarche_hist_attribue_par FOREIGN KEY (attribue_par) REFERENCES utilisateur(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE telegram_voice_ingest ADD CONSTRAINT fk_telegram_voice_ingest_canal_note FOREIGN KEY (canal_note_id) REFERENCES collab_canal_note(id) ON DELETE SET NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE telegram_voice_ingest DROP CONSTRAINT IF EXISTS fk_telegram_voice_ingest_canal_note")
    op.execute("ALTER TABLE tribu_patriarche_historique DROP CONSTRAINT IF EXISTS fk_tribu_patriarche_hist_attribue_par")
    op.execute("ALTER TABLE evenement_piece DROP CONSTRAINT IF EXISTS fk_evenement_piece_cree_par")
