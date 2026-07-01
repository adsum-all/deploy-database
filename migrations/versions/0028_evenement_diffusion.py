"""Live broadcast: stream kind and event visibility gating.

An event can carry a live stream. type_diffusion tells the client whether the
link is an embeddable stream (played inside the app) or an external meeting to
open in a new tab. visibilite gates who may see the link: public (great public,
served on the public route), membres (any authenticated member) or prive (staff
plus members registered to the event, i.e. with a participation record).

Revision ID: 0028_evenement_diffusion
Revises: 0027_anniversaire_annuaire
Create Date: 2026-07-01
"""
from __future__ import annotations

from alembic import op

revision = "0028_evenement_diffusion"
down_revision = "0027_anniversaire_annuaire"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE evenement ADD COLUMN IF NOT EXISTS type_diffusion text NOT NULL DEFAULT 'aucun'")
    op.execute("ALTER TABLE evenement DROP CONSTRAINT IF EXISTS evenement_type_diffusion_chk")
    op.execute(
        "ALTER TABLE evenement ADD CONSTRAINT evenement_type_diffusion_chk "
        "CHECK (type_diffusion IN ('embed', 'externe', 'aucun'))"
    )
    op.execute("ALTER TABLE evenement ADD COLUMN IF NOT EXISTS visibilite text NOT NULL DEFAULT 'membres'")
    op.execute("ALTER TABLE evenement DROP CONSTRAINT IF EXISTS evenement_visibilite_chk")
    op.execute(
        "ALTER TABLE evenement ADD CONSTRAINT evenement_visibilite_chk "
        "CHECK (visibilite IN ('public', 'membres', 'prive'))"
    )
    # Dedicated notification type for a broadcast test (message flags it as a test).
    op.execute(
        "INSERT INTO type_notification (cle, libelle, categorie, actif, scheduled) "
        "VALUES (%s, %s, %s, true, false) ON CONFLICT (cle) DO NOTHING",
        ("activite_test_diffusion", "Test de diffusion en live", "evenement"),
    )
    op.execute(
        "INSERT INTO modele_message (cle, titre, corps, titre_en, corps_en, categorie) "
        "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (cle) DO NOTHING",
        (
            "activite_test_diffusion",
            "Test de diffusion en live : {titre}",
            "Ceci est un test de diffusion en live pour {titre}. La session ouvrira bientot. (Test de diffusion en live.)",
            "Live broadcast test: {titre}",
            "This is a live broadcast test for {titre}. The session will open shortly. (Live broadcast test.)",
            "evenement",
        ),
    )


def downgrade() -> None:
    op.execute("DELETE FROM modele_message WHERE cle = 'activite_test_diffusion'")
    op.execute("DELETE FROM type_notification WHERE cle = 'activite_test_diffusion'")
    op.execute("ALTER TABLE evenement DROP CONSTRAINT IF EXISTS evenement_visibilite_chk")
    op.execute("ALTER TABLE evenement DROP COLUMN IF EXISTS visibilite")
    op.execute("ALTER TABLE evenement DROP CONSTRAINT IF EXISTS evenement_type_diffusion_chk")
    op.execute("ALTER TABLE evenement DROP COLUMN IF EXISTS type_diffusion")
