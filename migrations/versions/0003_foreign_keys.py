"""Add all foreign key constraints (DAT relations).

Adding foreign keys after every table exists resolves the DAT circular
references (membre <-> commission, utilisateur <-> membre) and cross-domain
references (events and counters reference utilisateur). One named constraint per
relation, exactly as the DAT prescribes.

Revision ID: 0003_foreign_keys
Revises: 0002_compte_parametrage
Create Date: 2026-06-28
"""
from __future__ import annotations

from alembic import op

revision = "0003_foreign_keys"
down_revision = "0002_compte_parametrage"
branch_labels = None
depends_on = None

# (constraint_name, table, column, ref_table, ref_column, on_delete)
FOREIGN_KEYS = [
    ("fk_commission_responsable", "commission", "responsable_id", "membre", "id", None),
    ("fk_membre_commission", "membre", "commission_id", "commission", "id", None),
    ("fk_appartenance_membre", "appartenance", "membre_id", "membre", "id", "CASCADE"),
    ("fk_appartenance_commission", "appartenance", "commission_id", "commission", "id", "CASCADE"),
    ("fk_engagement_membre", "engagement", "membre_id", "membre", "id", None),
    ("fk_document_membre", "document", "membre_id", "membre", "id", None),
    ("fk_document_traite_par", "document", "traite_par", "utilisateur", "id", None),
    ("fk_evenement_cree_par", "evenement", "cree_par", "utilisateur", "id", None),
    ("fk_terminal_controleur", "terminal", "controleur_id", "utilisateur", "id", None),
    ("fk_presence_membre", "presence", "membre_id", "membre", "id", None),
    ("fk_presence_evenement", "presence", "evenement_id", "evenement", "id", None),
    ("fk_presence_terminal", "presence", "terminal_id", "terminal", "id", None),
    ("fk_jeton_qr_membre", "jeton_qr", "membre_id", "membre", "id", None),
    ("fk_comptage_evenement", "comptage_volet_b", "evenement_id", "evenement", "id", None),
    ("fk_comptage_saisi_par", "comptage_volet_b", "saisi_par", "utilisateur", "id", None),
    ("fk_utilisateur_membre", "utilisateur", "membre_id", "membre", "id", None),
    ("fk_session_utilisateur", "session", "utilisateur_id", "utilisateur", "id", None),
    ("fk_notification_membre", "notification", "membre_id", "membre", "id", None),
    ("fk_parametre_maj_par", "parametre", "maj_par", "utilisateur", "id", None),
    ("fk_import_lot_importe_par", "import_lot", "importe_par", "utilisateur", "id", None),
    ("fk_recensement_reponse_recensement", "recensement_reponse", "recensement_id", "recensement", "id", None),
    ("fk_recensement_reponse_membre", "recensement_reponse", "membre_id", "membre", "id", None),
]


def upgrade() -> None:
    for name, table, column, ref_table, ref_column, on_delete in FOREIGN_KEYS:
        clause = (
            f"ALTER TABLE {table} ADD CONSTRAINT {name} "
            f"FOREIGN KEY ({column}) REFERENCES {ref_table}({ref_column})"
        )
        if on_delete:
            clause += f" ON DELETE {on_delete}"
        op.execute(clause)


def downgrade() -> None:
    for name, table, *_ in FOREIGN_KEYS:
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}")
