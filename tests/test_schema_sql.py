"""Offline schema assertions for the ADSUM migrations.

Runs ``alembic upgrade head --sql`` (offline, no database connection) and asserts
that the generated DDL matches the DAT: the 18 tables, the anti duplicate
constraint, the audit range partitioning, the foreign keys, the trigram index and
the baseline row level security. This proves the migrations are valid and exact
without needing a live database.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

import pytest

PROJECT = pathlib.Path(__file__).resolve().parents[1]

TABLES = [
    "membre", "commission", "appartenance", "engagement", "document",
    "evenement", "presence", "jeton_qr", "terminal", "comptage_volet_b",
    "utilisateur", "session", "audit", "notification",
    "parametre", "import_lot", "recensement", "recensement_reponse",
]


@pytest.fixture(scope="module")
def offline_sql() -> str:
    env = dict(os.environ, DATABASE_URL="postgresql+psycopg://localhost/adsum")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=PROJECT,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, f"alembic failed:\n{result.stderr}"
    return result.stdout.lower()


def test_all_18_tables_created(offline_sql: str) -> None:
    for table in TABLES:
        assert f"create table {table} " in offline_sql or f"create table {table}(" in offline_sql, (
            f"missing CREATE TABLE for {table}"
        )


def test_table_count(offline_sql: str) -> None:
    # Full schema at migration 0055: the 18 DAT domain tables plus everything the
    # later migrations added (extended domain tables, the two identifier counters,
    # etc.), the 13 audit partitions (12 months + default) and the alembic_version
    # bookkeeping table. Update this count whenever a migration adds or drops a table.
    assert offline_sql.count("create table ") == 87  # +4 tables from migrations 0082-0095


def test_audit_partition_count(offline_sql: str) -> None:
    assert offline_sql.count("partition of audit") == 13


def test_presence_unique_constraint(offline_sql: str) -> None:
    assert "unique (membre_id, evenement_id)" in offline_sql


def test_audit_is_range_partitioned(offline_sql: str) -> None:
    assert "partition by range (horodatage)" in offline_sql
    assert "primary key (id, horodatage)" in offline_sql
    assert "partition of audit default" in offline_sql


def test_foreign_keys_present(offline_sql: str) -> None:
    # Foreign keys across the full schema at migration 0055 (the 23 baseline
    # relations from revisions 0003/0006 plus those added by later migrations).
    assert offline_sql.count("add constraint fk_") == 45


def test_no_orphan_or_isolated_table(offline_sql: str) -> None:
    # Constitution I3: every table participates in at least one relation, as a
    # foreign key source (alter table T add constraint fk_) or target (references T).
    for table in TABLES:
        is_source = f"alter table {table} add constraint fk_" in offline_sql
        is_target = f"references {table}(" in offline_sql or f"references {table} (" in offline_sql
        assert is_source or is_target, f"{table} is isolated (no incoming or outgoing FK)"


def test_trigram_search_index(offline_sql: str) -> None:
    assert "using gin" in offline_sql
    assert "gin_trgm_ops" in offline_sql


def test_partial_active_qr_index(offline_sql: str) -> None:
    assert "where revoque = false" in offline_sql


def test_rls_enabled_on_every_table(offline_sql: str) -> None:
    # Constitution: row level security on every table. The count of ENABLE ROW
    # LEVEL SECURITY statements must equal the table count (test_table_count), so
    # every table is covered. Update both when a migration adds or drops a table.
    assert offline_sql.count("enable row level security") == 87


def test_rls_role_policies_created(offline_sql: str) -> None:
    # Role policies across the full schema at migration 0055 (the 35 baseline
    # policies from revision 0002 plus those added by later migrations). The
    # identifier counters need none: the owner bypasses RLS and anon/authenticated
    # were already revoked by 0042.
    assert offline_sql.count("create policy ") == 83  # + 2 groupe_permission (0076), + 2 invitation_engagement (0078)
    assert "adsum_current_role()" in offline_sql
