"""Development seed of realistic ADSUM data: organization, members and events.

Clearly separated and identified development data (Constitution I1 permits a seed
for the development environment). It is a no-op unless ADSUM_SEED_REAL is set to
"1", and every statement is idempotent, so running it twice changes nothing. It
never touches the existing operator account (ADS-000001).

It populates:
  - 3 coordinations, 4 intendances (geographic structures), 4 commissions and a
    few sous-commissions, matching the community organization;
  - 10 complete member profiles (genre, birth date, country-aware phone, city,
    intendance, commission, entry date, pastoral journey), two of them shepherds;
  - real-shaped Sacerdoce Royal events (KAIROS, Sunday gathering, formations,
    prayer vigil, adoration, yearly engagement renewal).

Run after ``alembic upgrade head`` with DATABASE_URL set and ADSUM_SEED_REAL=1.
"""
from __future__ import annotations

import os
import secrets
import sys
from datetime import UTC, date, datetime, timedelta

import psycopg
from argon2 import PasswordHasher

COORDINATIONS = [
    ("Coordination Afrique de l'Ouest", "Pays d'Afrique de l'Ouest"),
    ("Coordination Europe", "Pays d'Europe"),
    ("Coordination Amerique du Nord", "Pays d'Amerique du Nord"),
]

INTENDANCES = [
    ("Intendance Abidjan Nord", "Cote d'Ivoire", "Abidjan", "Coordination Afrique de l'Ouest"),
    ("Intendance Abidjan Sud", "Cote d'Ivoire", "Abidjan", "Coordination Afrique de l'Ouest"),
    ("Intendance Paris Centre", "France", "Paris", "Coordination Europe"),
    ("Intendance Montreal Ouest", "Canada", "Montreal", "Coordination Amerique du Nord"),
]

COMMISSIONS = [
    ("Accueil et Protocole", "Accueil des membres et protocole des celebrations"),
    ("Enseignement et Formation", "Catechese et formation des membres"),
    ("Intercession et Priere", "Priere, intercession et veillees"),
    ("Louange et Adoration", "Louange, chorale et adoration"),
]

SOUS_COMMISSIONS = [
    ("Protocole d'entree", "Accueil et Protocole"),
    ("Catechese des nouveaux", "Enseignement et Formation"),
    ("Veilleurs de priere", "Intercession et Priere"),
    ("Chorale", "Louange et Adoration"),
]

DIAL = {"Cote d'Ivoire": "+225", "France": "+33", "Canada": "+1"}

# The twelve tribes of Israel, each with the name of its patriarch (tribe leader).
TRIBUS = [
    ("Ruben", "Patriarche Emmanuel Kone"),
    ("Simeon", "Patriarche Joseph Yao"),
    ("Levi", "Patriarche Gabriel Toure"),
    ("Juda", "Patriarche Daniel Kouassi"),
    ("Dan", "Patriarche Samuel Bamba"),
    ("Nephtali", "Patriarche Andre Kone"),
    ("Gad", "Patriarche Etienne Aka"),
    ("Aser", "Patriarche Paul Diby"),
    ("Issacar", "Patriarche Marc Adou"),
    ("Zabulon", "Patriarche Luc N'Dri"),
    ("Joseph", "Patriarche Pierre Konan"),
    ("Benjamin", "Patriarche Jean Kouame"),
]

# Engagement level derived from the pastoral journey, plus marital and other data.
ENGAGEMENT = {
    "responsable": "responsable",
    "membre_actif": "engage",
    "en_accompagnement": "aspirant",
    "nouveau": "nouveau_engage",
    "en_pause": "membre_simple",
    "a_relancer": "membre_simple",
}
SITUATIONS = [
    ("marie", "religieux"),
    ("celibataire", None),
    ("en_couple", None),
    ("marie", "dot"),
    ("celibataire", None),
    ("marie", "dot_et_religieux"),
    ("fiance", None),
    ("marie", "religieux"),
    ("celibataire", None),
    ("marie", "dot"),
]
PROFESSIONS = [
    "Ingenieur", "Enseignante", "Infirmiere", "Comptable", "Etudiante",
    "Commercant", "Juriste", "Medecin", "Technicien", "Entrepreneur",
]
ETUDES = [
    "Bac+5", "Bac+3", "Bac+2", "Bac+5", "Bac+1",
    "Bac", "Bac+4", "Doctorat", "Bac+2", "Bac+3",
]

# (matricule, prenoms, nom, genre, naissance, pays, ville, intendance, commission,
#  groupe, entree, cheminement, est_berger)
MEMBERS = [
    ("ADS-000010", "Alexis", "Koutoua Amon", "homme", "1994-03-12", "Cote d'Ivoire", "Abidjan",
     "Intendance Abidjan Nord", "Louange et Adoration", "Groupe A", "2024-04-15", "membre_actif", False),
    ("ADS-000011", "Francois Xavier", "Bamba", "homme", "1989-07-21", "Cote d'Ivoire", "Abidjan",
     "Intendance Abidjan Nord", "Accueil et Protocole", "Groupe B", "2022-09-01", "responsable", False),
    ("ADS-000012", "Chantal Sophie", "Bernard", "femme", "1991-11-03", "France", "Paris",
     "Intendance Paris Centre", "Intercession et Priere", "Groupe A", "2023-01-20", "membre_actif", False),
    ("ADS-000013", "Pierre-Emmanuel", "Bertrand", "homme", "1985-02-17", "France", "Paris",
     "Intendance Paris Centre", "Enseignement et Formation", "Groupe C", "2021-06-10", "responsable", False),
    ("ADS-000014", "Nadia Sophie", "Bouchard", "femme", "1996-05-29", "Canada", "Montreal",
     "Intendance Montreal Ouest", "Louange et Adoration", "Groupe A", "2024-02-02", "en_accompagnement", False),
    ("ADS-000015", "Awa", "Traore", "femme", "1998-08-14", "Cote d'Ivoire", "Abidjan",
     "Intendance Abidjan Sud", "Intercession et Priere", "Groupe B", "2023-10-05", "a_relancer", False),
    ("ADS-000016", "Aya", "Kouame", "femme", "2000-01-09", "Cote d'Ivoire", "Abidjan",
     "Intendance Abidjan Sud", "Louange et Adoration", "Groupe A", "2026-05-18", "nouveau", False),
    ("ADS-000017", "Yao", "N'Guessan", "homme", "1987-12-25", "Cote d'Ivoire", "Abidjan",
     "Intendance Abidjan Sud", "Enseignement et Formation", "Groupe C", "2020-03-30", "en_pause", False),
    ("ADS-000018", "Sarah", "Diallo", "femme", "1986-04-04", "Cote d'Ivoire", "Abidjan",
     "Intendance Abidjan Nord", "Louange et Adoration", "Groupe A", "2019-07-18", "responsable", True),
    ("ADS-000019", "Marc", "Konate", "homme", "1983-09-11", "Cote d'Ivoire", "Abidjan",
     "Intendance Abidjan Sud", "Accueil et Protocole", "Groupe B", "2018-11-22", "responsable", True),
]

# (titre, type, volet, mode, jours_offset, duree_h, lieu)
EVENTS = [
    ("KAIROS 2026 - 16e edition", "rassemblement", "B", "presentiel", 30, 8, "Palais de la culture, Abidjan"),
    ("Rencontre du dimanche", "rencontre", "A", "presentiel", 3, 2, "Siege Sacerdoce Royal, Abidjan"),
    ("Veillee de priere", "priere", "A", "presentiel", 7, 4, "Siege Sacerdoce Royal, Abidjan"),
    ("Formation - Les fondements de la foi", "formation", "A", "hybride", 10, 2, "Salle Saint-Gabriel"),
    ("Exposition du Saint Sacrement", "adoration", "A", "presentiel", 5, 3, "Chapelle principale"),
    ("Renouvellement de l'engagement annuel", "celebration", "A", "presentiel", 21, 3, "Siege Sacerdoce Royal"),
    ("Office du matin", "rencontre", "A", "presentiel", -7, 3, "Salle principale"),
]


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        sys.exit("DATABASE_URL is not set. Export it before running the seed.")
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def _get_or_create(
    cur: psycopg.Cursor,
    table: str,
    where: str,
    params: tuple,
    insert_sql: str,
    insert_params: tuple,
) -> str:
    cur.execute(f"SELECT id FROM {table} WHERE {where}", params)
    row = cur.fetchone()
    if row:
        return str(row[0])
    cur.execute(insert_sql, insert_params)
    return str(cur.fetchone()[0])


def seed(conn: psycopg.Connection) -> None:
    hasher = PasswordHasher()
    with conn.cursor() as cur:
        coords = {
            nom: _get_or_create(
                cur, "coordination", "nom = %s", (nom,),
                "INSERT INTO coordination (nom, description) VALUES (%s, %s) RETURNING id", (nom, desc),
            )
            for nom, desc in COORDINATIONS
        }
        intendances = {
            nom: _get_or_create(
                cur, "intendance", "nom = %s", (nom,),
                "INSERT INTO intendance (nom, pays, ville, coordination_id) VALUES (%s, %s, %s, %s) RETURNING id",
                (nom, pays, ville, coords[coord]),
            )
            for nom, pays, ville, coord in INTENDANCES
        }
        commissions = {
            nom: _get_or_create(
                cur, "commission", "nom = %s", (nom,),
                "INSERT INTO commission (nom, description) VALUES (%s, %s) RETURNING id", (nom, desc),
            )
            for nom, desc in COMMISSIONS
        }
        for nom, comm in SOUS_COMMISSIONS:
            _get_or_create(
                cur, "sous_commission", "nom = %s", (nom,),
                "INSERT INTO sous_commission (nom, commission_id) VALUES (%s, %s) RETURNING id",
                (nom, commissions[comm]),
            )
        tribus = {
            nom: _get_or_create(
                cur, "tribu", "nom = %s", (nom,),
                "INSERT INTO tribu (nom, patriarche) VALUES (%s, %s) RETURNING id", (nom, patriarche),
            )
            for nom, patriarche in TRIBUS
        }

        member_ids: dict[str, str] = {}
        berger_users: dict[str, str] = {}
        for idx, m in enumerate(MEMBERS):
            (mat, prenoms, nom, genre, naissance, pays, ville, intendance, commission, groupe,
             entree, cheminement, est_berger) = m
            phone = f"{DIAL[pays]} 0{700000000 + idx * 111111}"
            email = f"{prenoms.split()[0].lower()}.{nom.split()[0].lower()}@example.com"
            mid = _get_or_create(
                cur, "membre", "matricule = %s", (mat,),
                """
                INSERT INTO membre
                    (matricule, email, nom, prenoms, telephone, genre, date_naissance, pays, ville,
                     intendance_id, commission_id, groupe, date_entree, cheminement_pastoral,
                     statut, statut_administratif, verifie)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'actif', 'valide', true)
                RETURNING id
                """,
                (mat, email, nom, prenoms, phone, genre, date.fromisoformat(naissance), pays, ville,
                 intendances[intendance], commissions[commission], groupe, date.fromisoformat(entree),
                 cheminement),
            )
            member_ids[mat] = mid

            tribu_nom = TRIBUS[idx % len(TRIBUS)][0]
            type_membre = "berger" if est_berger else ENGAGEMENT.get(cheminement, "membre_simple")
            has_promo = type_membre in ("engage", "responsable", "berger")
            promotion = f"Pierre Saint-Paul {idx % 3 + 1}" if has_promo else None
            situation, mariage = SITUATIONS[idx % len(SITUATIONS)]
            cur.execute(
                """
                UPDATE membre SET tribu_id = %s, type_membre = %s, promotion = %s,
                    situation_matrimoniale = %s, type_mariage = %s, profession = %s,
                    niveau_etudes = %s, baptise = %s, confirme = %s, premiere_communion = %s
                WHERE id = %s
                """,
                (tribus[tribu_nom], type_membre, promotion, situation, mariage,
                 PROFESSIONS[idx % len(PROFESSIONS)], ETUDES[idx % len(ETUDES)],
                 True, idx % 2 == 0, True, mid),
            )

            if est_berger:
                buid = _get_or_create(
                    cur, "utilisateur", "email = %s", (email,),
                    """
                    INSERT INTO utilisateur (email, hash_mdp, role, membre_id, actif)
                    VALUES (%s, %s, 'gestionnaire', %s, true) RETURNING id
                    """,
                    (email, hasher.hash(secrets.token_urlsafe(18)), mid),
                )
                berger_users[mat] = buid

        # Assign shepherds to a few members.
        sarah = berger_users.get("ADS-000018")
        marc = berger_users.get("ADS-000019")
        assignments = {
            "ADS-000010": sarah, "ADS-000014": sarah, "ADS-000016": sarah,
            "ADS-000011": marc, "ADS-000015": marc,
        }
        for mat, berger in assignments.items():
            if berger and mat in member_ids:
                cur.execute(
                    "UPDATE membre SET berger_referent_id = %s WHERE id = %s AND berger_referent_id IS NULL",
                    (berger, member_ids[mat]),
                )

        # General coordinators of the coordinations.
        for coord_nom, berger in (("Coordination Afrique de l'Ouest", sarah), ("Coordination Europe", marc)):
            if berger:
                cur.execute(
                    "UPDATE coordination SET responsable_id = %s WHERE nom = %s AND responsable_id IS NULL",
                    (berger, coord_nom),
                )

        now = datetime.now(UTC)
        for titre, type_, volet, mode, offset, duree, lieu in EVENTS:
            cur.execute("SELECT id FROM evenement WHERE titre = %s", (titre,))
            row = cur.fetchone()
            debut = now + timedelta(days=offset)
            fin = debut + timedelta(hours=duree)
            if row:
                cur.execute("UPDATE evenement SET debut = %s, fin = %s WHERE id = %s", (debut, fin, row[0]))
            else:
                cur.execute(
                    """
                    INSERT INTO evenement (titre, type, volet, mode, debut, fin, lieu, session_ouverte)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (titre, type_, volet, mode, debut, fin, lieu, offset == 3),
                )
    conn.commit()


def main() -> None:
    if os.environ.get("ADSUM_SEED_REAL") != "1":
        print("ADSUM_SEED_REAL is not '1': real demo seed skipped.")
        return
    with psycopg.connect(_database_url()) as conn:
        seed(conn)
    print("Real demo seed applied (idempotent): organization, 10 members, events.")


if __name__ == "__main__":
    main()
