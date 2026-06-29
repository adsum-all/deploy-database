"""Indexes, audit monthly partitions, and baseline row level security.

Indexes per the DAT performance strategy (search under 2 s, instant active QR,
recurring series, fast proof lookup). Audit is partitioned monthly for 2026 plus
a default partition so inserts never fail. Row level security is enabled on every
table as a deny-by-default baseline; per-role policies are added in Sprint 1.

Revision ID: 0004_indexes_partitions_rls
Revises: 0003_foreign_keys
Create Date: 2026-06-28
"""
from __future__ import annotations

from alembic import op

revision = "0004_indexes_partitions_rls"
down_revision = "0003_foreign_keys"
branch_labels = None
depends_on = None

ALL_TABLES = [
    "membre", "commission", "appartenance", "engagement", "document",
    "evenement", "presence", "jeton_qr", "terminal", "comptage_volet_b",
    "utilisateur", "session", "audit", "notification",
    "parametre", "import_lot", "recensement", "recensement_reponse",
]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # Indexes (DAT performance strategy).
    op.execute(
        "CREATE INDEX idx_membre_nom_trgm ON membre USING gin "
        "((coalesce(nom, '') || ' ' || coalesce(prenoms, '')) gin_trgm_ops)"
    )
    op.execute("CREATE INDEX idx_presence_evenement ON presence (evenement_id)")
    op.execute(
        "CREATE INDEX idx_jeton_qr_membre_actif ON jeton_qr (membre_id) WHERE revoque = false"
    )
    op.execute("CREATE INDEX idx_evenement_serie ON evenement (serie_id)")
    op.execute("CREATE INDEX idx_evenement_debut ON evenement (debut)")
    op.execute("CREATE INDEX idx_audit_objet ON audit (objet_type, objet_id)")
    op.execute(
        "CREATE INDEX idx_session_utilisateur_actif ON session (utilisateur_id) "
        "WHERE revoque = false"
    )

    # Audit monthly partitions for 2026 plus a default partition.
    for month in range(1, 13):
        start = f"2026-{month:02d}-01"
        end = "2027-01-01" if month == 12 else f"2026-{month + 1:02d}-01"
        op.execute(
            f"CREATE TABLE audit_2026_{month:02d} PARTITION OF audit "
            f"FOR VALUES FROM ('{start}') TO ('{end}')"
        )
    op.execute("CREATE TABLE audit_default PARTITION OF audit DEFAULT")

    # Baseline row level security: enable on every table (deny by default).
    # The backend connects through a privileged role that bypasses RLS; per-role
    # policies for member, controller, admin and direction land in Sprint 1.
    for table in ALL_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    for table in ALL_TABLES:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    for month in range(1, 13):
        op.execute(f"DROP TABLE IF EXISTS audit_2026_{month:02d}")
    op.execute("DROP TABLE IF EXISTS audit_default")
    for idx in (
        "idx_membre_nom_trgm", "idx_presence_evenement", "idx_jeton_qr_membre_actif",
        "idx_evenement_serie", "idx_evenement_debut", "idx_audit_objet",
        "idx_session_utilisateur_actif",
    ):
        op.execute(f"DROP INDEX IF EXISTS {idx}")
