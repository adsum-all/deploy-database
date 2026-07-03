"""Automated in-database health monitoring and access-anomaly detection.

Uses pg_cron (enabled on the project) to capture, every hour, a health snapshot
and flag anomalies without any external service:
- connection count and database size (saturation / growth),
- failed auth attempts in the last hour and the busiest source IP
  (brute-force / credential-stuffing signal, from auth_attempt),
- long-running queries currently active (slow-query signal).

An anomaly is flagged when failed attempts spike, a single IP hammers the auth
endpoints, or connections saturate. The history lives in db_surveillance so the
back office can surface it. This is the automated self-managing layer requested
for the database; a restore-to-staging test additionally needs a second project.

Revision ID: 0044_surveillance
Revises: 0043_canal_switch
Create Date: 2026-07-02
"""
from __future__ import annotations

from alembic import op

revision = "0044_surveillance"
down_revision = "0043_canal_switch"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS db_surveillance (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            capture_le timestamptz NOT NULL DEFAULT now(),
            connexions integer NOT NULL,
            taille_mb numeric NOT NULL,
            echecs_login_1h integer NOT NULL,
            ip_max_1h integer NOT NULL,
            requetes_lentes integer NOT NULL,
            anomalie boolean NOT NULL DEFAULT false,
            details jsonb NOT NULL DEFAULT '{}'::jsonb
        )
        """
    )
    op.execute("ALTER TABLE db_surveillance ENABLE ROW LEVEL SECURITY")
    op.execute("CREATE INDEX IF NOT EXISTS ix_db_surveillance_when ON db_surveillance (capture_le DESC)")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION capture_db_surveillance() RETURNS void
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_conn integer;
            v_size numeric;
            v_fail integer;
            v_ipmax integer;
            v_slow integer;
            v_top_ip text;
            v_anom boolean;
        BEGIN
            SELECT count(*) INTO v_conn FROM pg_stat_activity;
            SELECT round(pg_database_size(current_database()) / 1048576.0, 1) INTO v_size;
            SELECT count(*) INTO v_fail FROM auth_attempt WHERE cree_le > now() - interval '1 hour';
            SELECT coalesce(max(c), 0), coalesce((array_agg(ip_txt ORDER BY c DESC))[1], '')
              INTO v_ipmax, v_top_ip
              FROM (SELECT ip::text AS ip_txt, count(*) AS c FROM auth_attempt
                    WHERE cree_le > now() - interval '1 hour' GROUP BY ip) s;
            SELECT count(*) INTO v_slow FROM pg_stat_activity
              WHERE state = 'active' AND now() - query_start > interval '30 seconds'
                AND query NOT ILIKE '%capture_db_surveillance%';
            v_anom := (v_fail > 30) OR (v_ipmax > 15) OR (v_conn > 60);
            INSERT INTO db_surveillance (connexions, taille_mb, echecs_login_1h, ip_max_1h, requetes_lentes, anomalie, details)
            VALUES (v_conn, v_size, v_fail, v_ipmax, v_slow, v_anom,
                    jsonb_build_object('ip_suspecte', CASE WHEN v_ipmax > 15 THEN v_top_ip ELSE null END));
        END;
        $$;
        """
    )
    # Hourly capture. Unschedule any previous definition first (idempotent).
    op.execute(
        """
        DO $$
        BEGIN
            PERFORM cron.unschedule('adsum-db-surveillance')
            WHERE EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'adsum-db-surveillance');
            PERFORM cron.schedule('adsum-db-surveillance', '0 * * * *', 'SELECT capture_db_surveillance()');
        END $$;
        """
    )
    op.execute("SELECT capture_db_surveillance()")


def downgrade() -> None:
    op.execute("DO $$ BEGIN PERFORM cron.unschedule('adsum-db-surveillance') WHERE EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'adsum-db-surveillance'); END $$;")
    op.execute("DROP FUNCTION IF EXISTS capture_db_surveillance()")
    op.execute("DROP TABLE IF EXISTS db_surveillance")
