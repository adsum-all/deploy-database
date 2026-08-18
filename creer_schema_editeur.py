"""Créer le schéma commercial « editeur » et y appliquer les migrations.

Ce schéma porte les données de l'éditeur : organisations clientes, offres, commandes,
paiements, factures, déploiements, opérateurs. Il est séparé de « public », qui porte
les données métier d'une organisation, et cette séparation est la règle d'isolation
du produit : le commerce ne doit jamais partager une connexion avec le métier d'un
client.

Sans ce schéma, le service commerce répond 500 sur toutes ses routes, donc le portail
client et le catalogue du site vitrine sont vides.

L'opération est **additive et vérifiée** :

- elle refuse si le schéma contient déjà des tables, plutôt que d'écraser ;
- elle ne lit, ne modifie et ne supprime rien dans « public » ;
- elle applique les migrations dans l'ordre, en une seule transaction : si l'une
  échoue, aucune n'est conservée et la base reste dans l'état d'avant.

Usage :

    python creer_schema_editeur.py --verifier    # ne fait qu'inspecter
    python creer_schema_editeur.py --appliquer   # crée et migre
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
MIGRATIONS = RACINE / "services/adsum-commerce/migrations/versions"
SECRET = RACINE.parent / ".secret/supabase-secret-adsum.json"
SCHEMA = "editeur"


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


def etat(cur) -> dict:
    cur.execute("SELECT count(*) AS n FROM information_schema.tables "
                "WHERE table_schema = %s", (SCHEMA,))
    tables_editeur = cur.fetchone()["n"]
    cur.execute("SELECT count(*) AS n FROM information_schema.tables "
                "WHERE table_schema = 'public'")
    tables_public = cur.fetchone()["n"]
    return {"editeur": tables_editeur, "public": tables_public}


def verifier() -> int:
    with ouvrir() as conn, conn.cursor() as cur:
        courant = etat(cur)
        fichiers = sorted(MIGRATIONS.glob("*.sql"))
        print(f"Schéma « {SCHEMA} » : {courant['editeur']} tables")
        print(f"Schéma « public »   : {courant['public']} tables (métier, intouché)")
        print(f"Migrations à appliquer : {len(fichiers)}")
        for f in fichiers:
            print(f"  {f.name}")
        if courant["editeur"]:
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
            avant = etat(cur)
            if avant["editeur"]:
                print(f"Le schéma « {SCHEMA} » contient déjà {avant['editeur']} "
                      "tables. Rien n'est fait.", file=sys.stderr)
                return 1

            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
            # Le search_path est posé sur la session : sans lui, les migrations
            # écriraient dans « public », c'est-à-dire au milieu des tables métier.
            cur.execute(f"SET search_path TO {SCHEMA}")
            for f in fichiers:
                cur.execute(f.read_text(encoding="utf-8"))
                print(f"  appliquée : {f.name}")

            apres = etat(cur)
            if apres["public"] != avant["public"]:
                raise RuntimeError(
                    "Le nombre de tables de « public » a changé. Les migrations ont "
                    "écrit hors de leur schéma : tout est annulé.")
        conn.commit()
        print(f"\nSchema « {SCHEMA} » cree : {len(fichiers)} migrations, "
              f"{apres['editeur']} tables. « public » inchangé "
              f"({apres['public']} tables).")
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
