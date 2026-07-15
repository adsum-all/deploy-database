# ruff: noqa: E501 - migrations carry long SQL lines
"""Per-workspace dedicated instruction bot and its configuration lifecycle.

Each general workspace owns a dedicated Telegram instruction bot, strictly
separate from the member notification bot (@adsum_sr_bot). Because Telegram forbids
creating a bot programmatically, a configuration request is raised for the
back-office team, who create the bot in BotFather and paste its token/username.
The status tracks non_configure -> demande -> configure. Sub-spaces never own a
bot (they belong to their parent's instruction space).

Revision ID: 0126_espace_bot_instruction
Revises: 0125_canal_emetteurs
Create Date: 2026-07-11
"""
from __future__ import annotations

from alembic import op

revision = "0126_espace_bot_instruction"
down_revision = "0125_canal_emetteurs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE collab_espace ADD COLUMN IF NOT EXISTS instruction_bot_token text")
    op.execute("ALTER TABLE collab_espace ADD COLUMN IF NOT EXISTS instruction_bot_username text")
    op.execute(
        "ALTER TABLE collab_espace ADD COLUMN IF NOT EXISTS instruction_bot_statut text NOT NULL DEFAULT 'non_configure' "
        "CHECK (instruction_bot_statut IN ('non_configure', 'demande', 'configure'))"
    )
    op.execute("ALTER TABLE collab_espace ADD COLUMN IF NOT EXISTS instruction_config_demande_le timestamptz")
    op.execute("ALTER TABLE collab_espace ADD COLUMN IF NOT EXISTS instruction_config_par uuid REFERENCES utilisateur(id) ON DELETE SET NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_collab_espace_bot_statut ON collab_espace (instruction_bot_statut) WHERE parent_id IS NULL")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_collab_espace_bot_statut")
    for col in ("instruction_config_par", "instruction_config_demande_le", "instruction_bot_statut",
                "instruction_bot_username", "instruction_bot_token"):
        op.execute(f"ALTER TABLE collab_espace DROP COLUMN IF EXISTS {col}")
