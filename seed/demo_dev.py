"""Development-only seed so the member app has real content to display.

This is NOT production data and NOT fixtures hidden in application code. It is an
explicit, idempotent development seed (Constitution I1 allows a clearly separated
and identified seed for the development environment). It is a no-op unless the
environment variable ADSUM_SEED_DEMO is set to "1", and every statement is
idempotent, so running it twice changes nothing.

It populates, for the existing member ADS-000001:
  - one commission and the membership link;
  - a completed profile (name) for the provisional test member;
  - a few real-shaped events (one past, two upcoming);
  - one attendance record on the past event, to fill the history.

Run after ``alembic upgrade head`` with DATABASE_URL set and ADSUM_SEED_DEMO=1.
"""
from __future__ import annotations

import os
import sys
from datetime import UTC, datetime, timedelta

import psycopg

MATRICULE = "ADS-000001"
COMMISSION = "Commission Liturgie"


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        sys.exit("DATABASE_URL is not set. Export it before running the seed.")
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def _member_id(cur: psycopg.Cursor) -> str:
    cur.execute("SELECT id FROM membre WHERE matricule = %s", (MATRICULE,))
    row = cur.fetchone()
    if not row:
        sys.exit(f"Member {MATRICULE} not found. Provision the member before seeding demo data.")
    return str(row[0])


def _commission_id(cur: psycopg.Cursor) -> str:
    cur.execute("SELECT id FROM commission WHERE nom = %s", (COMMISSION,))
    row = cur.fetchone()
    if row:
        return str(row[0])
    cur.execute(
        "INSERT INTO commission (nom, description) VALUES (%s, %s) RETURNING id",
        (COMMISSION, "Commission chargee de la preparation liturgique."),
    )
    return str(cur.fetchone()[0])


def _link_member(cur: psycopg.Cursor, membre_id: str, commission_id: str) -> None:
    cur.execute(
        """
        UPDATE membre
        SET commission_id = %s,
            nom = COALESCE(nom, 'Membre'),
            prenoms = COALESCE(prenoms, 'Demonstration'),
            groupe = COALESCE(groupe, 'Groupe A')
        WHERE id = %s
        """,
        (commission_id, membre_id),
    )
    cur.execute(
        """
        INSERT INTO appartenance (membre_id, commission_id, role_local)
        VALUES (%s, %s, 'membre')
        ON CONFLICT (membre_id, commission_id) DO NOTHING
        """,
        (membre_id, commission_id),
    )


def _upsert_event(cur: psycopg.Cursor, titre: str, debut: datetime, fin: datetime, lieu: str) -> str:
    # Idempotent on the event title (unique within this seed). The start and end
    # are refreshed on every run so the demo events stay relative to today, while
    # never creating a duplicate row.
    cur.execute("SELECT id FROM evenement WHERE titre = %s", (titre,))
    row = cur.fetchone()
    if row:
        cur.execute(
            "UPDATE evenement SET debut = %s, fin = %s, lieu = %s WHERE id = %s",
            (debut, fin, lieu, row[0]),
        )
        return str(row[0])
    cur.execute(
        """
        INSERT INTO evenement (titre, type, volet, mode, debut, fin, lieu)
        VALUES (%s, 'reunion', 'A', 'presentiel', %s, %s, %s)
        RETURNING id
        """,
        (titre, debut, fin, lieu),
    )
    return str(cur.fetchone()[0])


def seed(conn: psycopg.Connection) -> None:
    now = datetime.now(UTC)
    with conn.cursor() as cur:
        membre_id = _member_id(cur)
        commission_id = _commission_id(cur)
        _link_member(cur, membre_id, commission_id)

        past = _upsert_event(
            cur, "Messe dominicale", now - timedelta(days=7, hours=1),
            now - timedelta(days=7), "Chapelle principale",
        )
        _upsert_event(
            cur, "Reunion de la Commission Liturgie", now + timedelta(days=3),
            now + timedelta(days=3, hours=2), "Salle Saint-Gabriel",
        )
        _upsert_event(
            cur, "Veillee de priere", now + timedelta(days=10),
            now + timedelta(days=10, hours=3), "Grande salle",
        )

        cur.execute(
            """
            INSERT INTO presence (membre_id, evenement_id, mode, arrivee, depart, methode)
            VALUES (%s, %s, 'presentiel', %s, %s, 'qr')
            ON CONFLICT (membre_id, evenement_id) DO NOTHING
            """,
            (membre_id, past, now - timedelta(days=7, hours=1), now - timedelta(days=7)),
        )

        _seed_notifications(cur, membre_id)
    conn.commit()


NOTIFICATIONS = [
    ("identite", "Identite validee", "Votre carte et votre QR sont actifs.", True),
    ("rappel", "Rappel : Reunion de la Commission Liturgie", "Dans 3 jours, salle Saint-Gabriel.", False),
    ("recensement", "Recensement annuel ouvert", "Confirmez votre engagement avant l'echeance.", False),
]


def _seed_notifications(cur: psycopg.Cursor, membre_id: str) -> None:
    for type_, titre, corps, lu in NOTIFICATIONS:
        cur.execute(
            "SELECT 1 FROM notification WHERE membre_id = %s AND titre = %s",
            (membre_id, titre),
        )
        if cur.fetchone():
            continue
        cur.execute(
            """
            INSERT INTO notification (membre_id, type, titre, corps, lu, envoye_le)
            VALUES (%s, %s, %s, %s, %s, now())
            """,
            (membre_id, type_, titre, corps, lu),
        )


def main() -> None:
    if os.environ.get("ADSUM_SEED_DEMO") != "1":
        print("ADSUM_SEED_DEMO is not '1': development demo seed skipped.")
        return
    with psycopg.connect(_database_url()) as conn:
        seed(conn)
    print("Development demo seed applied (idempotent).")


if __name__ == "__main__":
    main()
