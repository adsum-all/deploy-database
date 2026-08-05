# ruff: noqa: E501 - migrations carry long SQL lines
"""Make the platform access that an application tag granted by accident explicit.

A group handed out from an application tab is written with portee_type='global' and
an application_code. The tag was meant to bound the right to that application. It
never did: the resolver ignored it, so the right applied everywhere, and the cached
account role was raised from it. Someone granted Administration inside the
collaboration workspace held Administration in the back office too.

The enforcement is about to change so a tagged membership stops elevating the account
role. Applied as-is that would silently demote whoever depends on such a membership
today, which is an outage caused by a security fix.

The tag is therefore cleared on the memberships that are the sole source of an
account's platform role. Clearing it, rather than adding an untagged twin, is not a
stylistic choice: membre_groupe_scope_uniq spans (membre, groupe, portee, portee_id)
and ignores application_code, so a twin cannot exist. Clearing cannot collide, since
the row already occupies its slot.

What this changes, deliberately: such a membership leaves the application revocation
cascade, which deletes memberships by application_code. That is the honest outcome.
A right that reaches the whole platform is not an application access, and revoking it
should be a decision somebody takes in the groups screen, not a side effect of
withdrawing the visibility of one application.

Nothing is granted here that was not already effective.

Revision ID: 0179_acces_applicatif_explicite
Revises: 0178_cle_webhook_email
Create Date: 2026-07-28
"""
from __future__ import annotations

from alembic import op

revision = "0179_acces_applicatif_explicite"
down_revision = "0178_cle_webhook_email"
branch_labels = None
depends_on = None

# Same ranking the application uses to pick the highest role a member's groups grant.
_RANG = (
    "CASE {col} WHEN 'super_admin' THEN 5 WHEN 'admin' THEN 4 "
    "WHEN 'direction' THEN 3 WHEN 'gestionnaire' THEN 2 ELSE 1 END"
)


def upgrade() -> None:
    op.execute(
        f"""
        UPDATE membre_groupe mg
           SET application_code = NULL
          FROM groupe_acces g
         WHERE g.id = mg.groupe_id
           AND mg.actif = true
           AND g.actif = true
           AND mg.application_code IS NOT NULL
           AND mg.portee_type = 'global'
           AND g.mode = 'role'
           AND g.role_accorde IS NOT NULL
           AND g.role_accorde <> 'membre'
           -- Only when nothing else already grants a role at least as high. Where
           -- another membership carries the account, the tagged one changes nothing
           -- and can keep both its tag and its place in the revocation cascade.
           AND NOT EXISTS (
               SELECT 1
                 FROM membre_groupe m2
                 JOIN groupe_acces g2 ON g2.id = m2.groupe_id
                WHERE m2.membre_id = mg.membre_id
                  AND m2.id <> mg.id
                  AND m2.actif = true
                  AND g2.actif = true
                  AND m2.application_code IS NULL
                  AND m2.portee_type = 'global'
                  AND g2.mode = 'role'
                  AND {_RANG.format(col='g2.role_accorde')} >= {_RANG.format(col='g.role_accorde')}
           )
        """
    )


def downgrade() -> None:
    # The tag is not restored: which application a now-platform-wide grant used to
    # claim is not recoverable from the row, and guessing would re-attach a real
    # access to a revocation cascade that would then delete it.
    pass
