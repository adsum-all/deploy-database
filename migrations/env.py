"""Alembic environment for the ADSUM schema.

The database URL is taken from the DATABASE_URL environment variable so that no
credential is ever stored in the repository (Constitution I10). Offline mode
(``alembic upgrade head --sql``) needs only a dialect, so a local placeholder URL
is accepted there.
"""
from __future__ import annotations

import os

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

# Migrations use explicit op.execute DDL that matches the DAT exactly, so there is
# no autogenerate target metadata.
target_metadata = None

# Offline SQL generation only needs a PostgreSQL dialect, not a live connection.
DEFAULT_OFFLINE_URL = "postgresql+psycopg://localhost/adsum"


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return url
    if context.is_offline_mode():
        return DEFAULT_OFFLINE_URL
    raise RuntimeError(
        "DATABASE_URL is not set. Export it before running online migrations, "
        "for example postgresql+psycopg://user:password@host:5432/postgres."
    )


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
