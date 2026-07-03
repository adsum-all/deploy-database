"""Alembic environment for the ADSUM schema.

The database URL is taken from the DATABASE_URL environment variable so that no
credential is ever stored in the repository (Constitution I10). Offline mode
(``alembic upgrade head --sql``) needs only a dialect, so a local placeholder URL
is accepted there.
"""
from __future__ import annotations

import datetime as _dt
import os

import alembic.op as _alembic_op
from alembic import context
from sqlalchemy import engine_from_config, pool

# Compatibility shim. Several migrations call ``op.execute(sql, params)`` with
# psycopg-style ``%s`` placeholders because they are also applied in production
# through a lightweight ``op.execute(sql, params)`` harness. Standard Alembic
# ``op.execute`` only takes the SQL text, so the parameterised form broke both
# ``alembic upgrade head --sql`` (offline) and the offline schema test. This
# wrapper inlines the params as safe SQL literals and calls the standard
# ``op.execute`` with plain text. Direct literal rendering is used (not a
# SQLAlchemy ``text()`` clause) because the migrations rely on PostgreSQL ``::``
# casts, which collide with SQLAlchemy's ``:name`` bind syntax. It loads only
# under real Alembic (this env.py), never under the production harness, which
# stubs ``alembic.op`` itself, so the deployment path is untouched.
_orig_execute = _alembic_op.execute


def _sql_literal(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return repr(value)
    text = value.isoformat() if isinstance(value, (_dt.date, _dt.datetime)) else str(value)
    return "'" + text.replace("'", "''") + "'"


def _execute_with_params(sqltext, params=None, execution_options=None):  # noqa: ANN001, ANN202
    if params is None or not isinstance(sqltext, str):
        return _orig_execute(sqltext, execution_options=execution_options)
    segments = sqltext.split("%s")
    if len(segments) - 1 != len(params):
        # Placeholder count does not match: leave it to the original call.
        return _orig_execute(sqltext, execution_options=execution_options)
    rendered = segments[0]
    for value, tail in zip(params, segments[1:], strict=True):
        rendered += _sql_literal(value) + tail
    return _orig_execute(rendered, execution_options=execution_options)


_alembic_op.execute = _execute_with_params

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
