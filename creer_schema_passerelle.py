"""Créer le schéma « passerelle » et y appliquer ses migrations.

Ce schéma porte le registre des envois de l'éditeur : ce qui est parti, par quel
canal, vers quelle empreinte d'adresse, avec quel résultat. Il est séparé de
« public », qui porte les données métier d'une organisation, et de « editeur », qui
porte les données commerciales.

La séparation n'est pas cosmétique. L'hébergement expose « public » par une API
automatique accessible à un rôle anonyme : des tables posées là seraient lisibles
sans aucune authentification applicative. C'est précisément ce que ce script
empêche, en créant le schéma et en posant le chemin de recherche **avant**
d'appliquer la moindre migration.

L'opération est additive et vérifiée, comme celle du schéma commercial :

- elle refuse si le schéma contient déjà des tables, plutôt que d'écraser ;
- elle ne lit, ne modifie et ne supprime rien dans « public » ni dans « editeur » ;
- elle applique les migrations en une seule transaction : si l'une échoue, aucune
  n'est conservée ;
- elle vérifie après coup qu'aucune table n'a atterri ailleurs que dans le schéma
  visé, ce qui est le défaut exact contre lequel ce script existe.

Usage :

    python creer_schema_passerelle.py --verifier    # ne fait qu'inspecter
    python creer_schema_passerelle.py --appliquer   # crée et migre
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
MIGRATIONS = RACINE / "services/adsum-gateway/migrations/versions"
SECRET = RACINE.parent / ".secret/supabase-secret-adsum.json"
SCHEMA = "passerelle"


def dsn() -> str:
    """La chaîne de connexion, lue du coffre local. Jamais affichée."""
    s = json.load(open(SECRET, encoding="utf-8"))["supabase"]
    mdp = urllib.parse.quote(s["db_password"], safe="")
    return (f"postgresql://postgres.{s['project_id']}:{mdp}"
            f"@aws-0-{s['region']}.pooler.supabase.com:5432/postgres?sslmode=require")


def ouvrir():
    import psycopg
    from psycopg.rows import dict_row

    return psycopg.connect(dsn(), row_factory=dict_row, connect_timeout=20)


def compter(cur, schema: str) -> int:
    cur.execute("SELECT count(*) AS n FROM information_schema.tables "
                "WHERE table_schema = %s", (schema,))
    return cur.fetchone()["n"]


def verifier() -> int:
    with ouvrir() as conn, conn.cursor() as cur:
        fichiers = sorted(MIGRATIONS.glob("*.sql"))
        print(f"Schéma « {SCHEMA} »  : {compter(cur, SCHEMA)} tables")
        print(f"Schéma « public »     : {compter(cur, 'public')} tables (métier, intouché)")
        print(f"Schéma « editeur »    : {compter(cur, 'editeur')} tables (commercial, intouché)")
        print(f"Migrations à appliquer : {len(fichiers)}")
        for f in fichiers:
            print(f"  {f.name}")
        if compter(cur, SCHEMA):
            print("\nDéjà peuplé : l'application serait refusée.")
        return 0


def appliquer() -> int:
    fichiers = sorted(MIGRATIONS.glob("*.sql"))
    if not fichiers:
        print(f"Aucune migration dans {MIGRATIONS}", file=sys.stderr)
        return 2

    conn = ouvrir()
    try:
        with conn.cursor() as cur:
            avant_schema = compter(cur, SCHEMA)
            if avant_schema:
                print(f"Le schéma « {SCHEMA} » contient déjà {avant_schema} tables. "
                      "Rien n'est fait.", file=sys.stderr)
                return 1
            avant_public = compter(cur, "public")

            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
            # Le chemin de recherche, posé avant toute migration. C'est la seule
            # chose qui empêche les tables d'atterrir dans « public », où elles
            # seraient exposées sans authentification.
            cur.execute(f"SET search_path TO {SCHEMA}")
            for f in fichiers:
                cur.execute(f.read_text(encoding="utf-8"))
                print(f"  appliquée : {f.name}")

            apres_schema = compter(cur, SCHEMA)
            if compter(cur, "public") != avant_public:
                raise RuntimeError(
                    "Le nombre de tables de « public » a changé. Une migration a "
                    "écrit hors de son schéma : tout est annulé.")
            if apres_schema == 0:
                raise RuntimeError(
                    f"Aucune table dans « {SCHEMA} » après application. Le chemin de "
                    "recherche n'a pas tenu : tout est annulé.")
        conn.commit()
        print(f"\nSchéma « {SCHEMA} » créé : {len(fichiers)} migration(s), "
              f"{apres_schema} tables. « public » inchangé ({avant_public} tables).")
        print("\nPensez à poser ADSUM_PASSERELLE_POIVRE sur le service : sans lui, "
              "il refusera de condenser une adresse et donc d'envoyer.")
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main() -> int:
    analyseur = argparse.ArgumentParser(description=__doc__)
    groupe = analyseur.add_mutually_exclusive_group(required=True)
    groupe.add_argument("--verifier", action="store_true",
                        help="Inspecter sans rien écrire")
    groupe.add_argument("--appliquer", action="store_true",
                        help="Créer le schéma et appliquer les migrations")
    arguments = analyseur.parse_args()
    return verifier() if arguments.verifier else appliquer()


if __name__ == "__main__":
    sys.exit(main())
