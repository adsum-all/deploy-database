"""Apply the real referential seed for ADSUM.

This script seeds only configuration and a real super administrator:

- the ``parametre`` table with documented default system parameters;
- one super administrator account, built from the environment variables
  ADSUM_SUPERADMIN_EMAIL and ADSUM_SUPERADMIN_PASSWORD, with the password hashed
  with Argon2. No credential is ever hardcoded (Constitution I10).

It never inserts fictional members, presences, commissions or events
(Constitution I1). Run it after ``alembic upgrade head`` with DATABASE_URL set.
"""
from __future__ import annotations

import json
import os
import sys

import psycopg
from argon2 import PasswordHasher
from parametres import DEFAULT_PARAMETERS


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        sys.exit("DATABASE_URL is not set. Export it before running the seed.")
    # psycopg expects a plain postgresql:// URL, not the SQLAlchemy +psycopg form.
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def seed_parametres(conn: psycopg.Connection) -> int:
    count = 0
    with conn.cursor() as cur:
        for cle, valeur, categorie, description in DEFAULT_PARAMETERS:
            cur.execute(
                """
                INSERT INTO parametre (cle, valeur, categorie, description)
                VALUES (%s, %s::jsonb, %s, %s)
                ON CONFLICT (cle) DO NOTHING
                """,
                (cle, json.dumps(valeur), categorie, description),
            )
            count += cur.rowcount
    return count


def seed_super_admin(conn: psycopg.Connection) -> bool:
    email = os.environ.get("ADSUM_SUPERADMIN_EMAIL", "").strip()
    password = os.environ.get("ADSUM_SUPERADMIN_PASSWORD", "")
    if not email or not password:
        print(
            "No super admin seeded: set ADSUM_SUPERADMIN_EMAIL and "
            "ADSUM_SUPERADMIN_PASSWORD to create the real super administrator."
        )
        return False
    hashed = PasswordHasher().hash(password)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO utilisateur (email, hash_mdp, role, actif, double_facteur)
            VALUES (%s, %s, 'super_admin', true, true)
            ON CONFLICT (email) DO NOTHING
            """,
            (email, hashed),
        )
        created = cur.rowcount == 1
    print("Super admin created." if created else "Super admin already present.")
    return created


def main() -> None:
    with psycopg.connect(_database_url()) as conn:
        params = seed_parametres(conn)
        seed_super_admin(conn)
        conn.commit()
        print(f"Seed complete: {params} new parametre row(s).")


if __name__ == "__main__":
    main()
