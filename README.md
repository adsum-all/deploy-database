# database

Part of the ADSUM platform (membership, QR check-in and attendance).
Subgroup: `deployment`.

## Role

Single source of the schema: PostgreSQL migrations (Alembic) and realistic referential seed. 17 tables of the DAT.

## Stack

Python, SQLAlchemy, Alembic, PostgreSQL 16.

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
