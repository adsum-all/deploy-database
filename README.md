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

## CI

Pipelines are defined in `.gitlab-ci.yml`, which includes the shared templates
from `sr-media-ai/adsum/deployment/ci-templates`.
