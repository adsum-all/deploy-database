# database

![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17.6-4169E1?logo=postgresql&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-hosted-3FCF8E?logo=supabase&logoColor=white)
![Alembic](https://img.shields.io/badge/Alembic-1.18-6BA81E)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?logo=sqlalchemy&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)

Part of the ADSUM platform (membership, QR check-in and attendance).
Subgroup: `deployment`.

## Role

Single source of the schema: PostgreSQL migrations (Alembic) and realistic referential seed. 17 tables of the DAT.

## Stack

Alembic migrations (versioned, single source of the schema) over SQLAlchemy core and
psycopg 3, applied to a PostgreSQL 17.6 database hosted on Supabase. No application ORM:
the API talks to the same database directly. Exact versions in the table at the bottom.

## Conventions

- Branches: work on `feature/*` or `fix/*` from `develop`, then a merge request.
  Merge order `feature/* -> develop -> main`. Never push to `main`.
- Constitution (zero tolerance): no mock data, no file over 500 lines,
  no em-dash (U+2014 / U+2013), no secret in clear. CI enforces these.
- Commit messages in English, Conventional Commits.

## Schema (Sprint 0)

The 18 tables defined by the DAT data model are created by the Alembic migrations
in `migrations/versions/`, in four steps to resolve the DAT circular references:

1. `0001_identite_activite` - identity and activity tables (10), no cross FK.
2. `0002_compte_parametrage` - account, traceability, settings, campaigns (8).
3. `0003_foreign_keys` - all 22 foreign key constraints.
4. `0004_indexes_partitions_rls` - indexes, audit monthly partitions, baseline RLS.

The DAT prose says 17 tables while its DDL defines 18; the audit table needs the
partition key in its primary key. Both points are recorded in `docs/adr`
(ADR-0001). No table is invented or omitted.

## Usage

```
py -3 -m venv .venv
.venv/Scripts/python -m pip install -e .[dev]
export DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/postgres
.venv/Scripts/python -m alembic upgrade head
# real referential seed (parameters always, super admin only if env is set):
export ADSUM_SUPERADMIN_EMAIL=... ADSUM_SUPERADMIN_PASSWORD=...
.venv/Scripts/python seed/seed.py
```

`DATABASE_URL` is read from the environment only, never stored in the repository
(Constitution I10). The seed inserts documented default system parameters and,
when the two env variables are set, one real super administrator (Argon2 hashed).
It never inserts fictional members, presences, commissions or events (I1).

## Tests

`pytest` runs offline schema assertions: it generates the DDL with
`alembic upgrade head --sql` and checks the 18 tables, the anti duplicate
constraint, the audit range partitioning, the 22 foreign keys, the trigram search
index and the baseline row level security.

## CI

Pipelines are defined in `.gitlab-ci.yml`, which includes the shared templates
from `sr-media-ai/adsum/deployment/ci-templates`.

## Stack technique, versions exactes

Versions testées et déployées (relevées via `pip freeze` dans `.venv`, et `SHOW server_version` sur la base Supabase de production).

| Composant | Rôle | Version exacte |
| --- | --- | --- |
| PostgreSQL (Supabase) | Base de données | 17.6 |
| Python | Runtime des migrations | 3.13.7 |
| Alembic | Moteur de migrations | 1.18.5 |
| SQLAlchemy | Core SQL (pas d'ORM applicatif) | 2.0.51 |
| psycopg / psycopg-binary | Driver PostgreSQL | 3.3.4 |
| greenlet | Support async SQLAlchemy | 3.5.3 |

Tête de migration courante : `0168_equipes_speciales`. Schéma : 137 tables, RLS active sur 137 tables, 183 policies de rôle.
