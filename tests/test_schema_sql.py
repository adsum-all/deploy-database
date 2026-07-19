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
    # +5 collab enrichment tables (0096); +6 space tables (0097, collab_carte_membre
    # is dropped and recreated against utilisateur, hence counted twice); +6 social
    # tables (0098); +1 evenement_piece attachments table (0103); +1 collab_item_assigne
    # join table (0106); +1 collab_presence live-viewer table (0107). The net live table
    # set stays coherent (see the prod proof). Migrations 0104 and 0105 only add columns.
    # +4 since 0107: ai_provider_config (0109), the three moderator-channel tables
    # collab_canal_message/note/reponse (0110). 0111-0116 only add columns/constraints
    # or policies. This count had drifted (was 106) before the 0116 RLS audit.
    # +1 at 0119: telegram_voice_ingest (Telegram voice-note ingestion ledger).
    # +5 for the access-governance surface (application, membre_application_acces,
    # application_role, membre_application_role and the applications catalogue tables).
    # +1 at 0145: collab_tableau_favori (per-account board stars).
    # +1 at 0147: cible_activite (administrable activity targeting referential).
    # +4 at 0150: the organisation-chart tables (organisation_version/node/link/changelog).
    assert offline_sql.count("create table ") == 130


def test_audit_partition_count(offline_sql: str) -> None:
    assert offline_sql.count("partition of audit") == 13


def test_presence_unique_constraint(offline_sql: str) -> None:
    assert "unique (membre_id, evenement_id)" in offline_sql


def test_audit_is_range_partitioned(offline_sql: str) -> None:
    assert "partition by range (horodatage)" in offline_sql
    assert "primary key (id, horodatage)" in offline_sql
    assert "partition of audit default" in offline_sql


def test_foreign_keys_present(offline_sql: str) -> None:
    # Foreign keys across the full schema (the 23 baseline relations from 0003/0006
    # plus those added by later migrations, plus the 7 collaboration actor FKs to
    # utilisateur added by 0099, plus the 3 internal-reference FKs added by 0143,
    # plus the 2 collab_tableau_favori FKs added by 0145, plus the 3 FKs of 0147
    # (cible_activite audit columns and evenement.cible_type -> cible_activite).
    assert offline_sql.count("add constraint fk_") == 61


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
    # Constitution: row level security on every table. Migration 0116 closed the
    # last gaps (seven tables that shipped without RLS: the three moderator-channel
    # tables, collab_item_assigne, collab_presence, evenement_piece,
    # notification_echec). The statement count exceeds the distinct table count by
    # one because a single table is re-enabled across two migrations (idempotent).
    # The real invariant is verified against production: zero tables without RLS.
    # +1 at 0119: telegram_voice_ingest. +1 at 0145: collab_tableau_favori.
    # +1 at 0147: cible_activite.
    # +4 at 0151: RLS enabled on the four organisation-chart tables (0150).
    assert offline_sql.count("enable row level security") == 130


def test_rls_role_policies_created(offline_sql: str) -> None:
    # Role policies across the full schema at migration 0055 (the 35 baseline
    # policies from revision 0002 plus those added by later migrations). The
    # identifier counters need none: the owner bypasses RLS and anon/authenticated
    # were already revoked by 0042.
    # 2 policies per new collab table across 0096 (5), 0097 (5: espace, espace_membre,
    # demande_acces, tableau_participant, carte_membre; collab_etiquette keeps its
    # 0096 policies and is NOT re-policied) and 0098 (6): 93 + 22 = 115.
    # +16 from 0116: niveau_engagement (2) and the seven newly RLS-enabled tables
    # (2 each) = 115 + 16 = 131.
    # +2 from 0119: telegram_voice_ingest (select + write) = 133.
    # +2 from 0145: collab_tableau_favori (select + write).
    # +2 from 0147: cible_activite (select + write).
    # +8 from 0151: select + write on the four organisation-chart tables (0150).
        # +4 from 0154: select + write on information and information_destinataire.
    assert offline_sql.count("create policy ") == 169
    assert "adsum_current_role()" in offline_sql
