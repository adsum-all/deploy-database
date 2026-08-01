# ruff: noqa: E501 - migrations carry long SQL lines
"""Make the session delay and the attendance windows settings, not constants.

Three durations were decided in the code and could not be changed by the people who
live with them.

A session lasted its whole natural life whatever happened in between, so an
administrator who walked away from an open back office left a working session behind
them. Nothing closed it, because nothing recorded whether it was still being used.

The attendance window was the literal ``interval '2 hours'``, repeated in four
queries. An organisation whose prayer runs forty minutes had no way to say so, and one
that wanted a quarter of an hour of tolerance had no way either.

And the per-activity override was expressed in HOURS, so the shortest window anybody
could set was one hour: exactly the granularity that was asked for and could not be
given.

All three become settings in MINUTES, which is the unit that expresses both a quarter
of an hour and a whole day. Nothing is imposed: the values below reproduce today's
behaviour, so applying this migration changes nothing until somebody decides
otherwise. That matters because this platform is meant to serve organisations that
have not been met yet, and their habits are not ours to hard-code.

Revision ID: 0183_session_et_fenetres
Revises: 0182_bibliotheque_documentaire
Create Date: 2026-07-30
"""
from __future__ import annotations

from alembic import op

revision = "0183_session_et_fenetres"
down_revision = "0182_bibliotheque_documentaire"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # When the session was last seen alive. Nullable: existing sessions have no
    # history, and the reader falls back to their opening time.
    op.execute("ALTER TABLE session ADD COLUMN IF NOT EXISTS derniere_activite timestamptz")
    op.execute(
        "CREATE INDEX IF NOT EXISTS session_activite_idx ON session (derniere_activite) "
        "WHERE fin IS NULL AND revoque = false"
    )

    # A per-activity response window in MINUTES, alongside the one in hours which
    # stays for the activities already carrying it. The reader prefers the minutes
    # when both are set, so nothing already scheduled changes meaning.
    op.execute("ALTER TABLE evenement ADD COLUMN IF NOT EXISTS fenetre_reponse_minutes int")
    op.execute(
        "ALTER TABLE evenement DROP CONSTRAINT IF EXISTS evenement_fenetre_reponse_minutes_bornes"
    )
    op.execute(
        "ALTER TABLE evenement ADD CONSTRAINT evenement_fenetre_reponse_minutes_bornes "
        "CHECK (fenetre_reponse_minutes IS NULL OR (fenetre_reponse_minutes >= 0 AND fenetre_reponse_minutes <= 20160))"
    )
    # Carry over what was already chosen in hours, so an activity keeps its window
    # and the interface can show it in minutes straight away.
    op.execute(
        "UPDATE evenement SET fenetre_reponse_minutes = fenetre_reponse_heures * 60 "
        "WHERE fenetre_reponse_minutes IS NULL AND fenetre_reponse_heures IS NOT NULL"
    )

    # The three new settings, each holding the value the code used until now.
    reglages = [
        # Sign out a session left idle this long. Four hours: long enough not to
        # interrupt a working afternoon, short enough that a forgotten screen on a
        # shared computer does not stay open all night. 0 switches it off.
        ("session_inactivite_minutes", "240"),
        # How long before an activity starts the attendance window opens. Was the
        # literal 15 minutes.
        ("pointage_ouverture_avant_minutes", "15"),
        # How long an activity stays open for attendance when no end time is set.
        # Was the literal 2 hours.
        ("pointage_duree_defaut_minutes", "120"),
    ]
    valeurs = ", ".join("(%s, %s::jsonb)" for _ in reglages)
    params: list[str] = []
    for cle, valeur in reglages:
        params.extend([cle, valeur])
    # One multi-row statement rather than a loop: the pooled connection reuses
    # prepared statement names, and a loop collides on them.
    op.get_bind().exec_driver_sql(
        f"INSERT INTO parametre (cle, valeur) VALUES {valeurs} ON CONFLICT (cle) DO NOTHING",
        tuple(params),
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM parametre WHERE cle IN "
        "('session_inactivite_minutes', 'pointage_ouverture_avant_minutes', 'pointage_duree_defaut_minutes')"
    )
    op.execute("ALTER TABLE evenement DROP CONSTRAINT IF EXISTS evenement_fenetre_reponse_minutes_bornes")
    op.execute("ALTER TABLE evenement DROP COLUMN IF EXISTS fenetre_reponse_minutes")
    op.execute("DROP INDEX IF EXISTS session_activite_idx")
    op.execute("ALTER TABLE session DROP COLUMN IF EXISTS derniere_activite")
