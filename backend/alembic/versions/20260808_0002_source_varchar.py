"""Store listings.source as VARCHAR so 'manual' submissions work on Postgres.

Revision ID: 20260808_0002
Revises: 20260808_0001
Create Date: 2026-08-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260808_0002"
down_revision = "20260808_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(
        "ALTER TABLE listings ALTER COLUMN source TYPE VARCHAR(32) USING source::text"
    )
    op.execute("DROP TYPE IF EXISTS sourceplatform")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE sourceplatform AS ENUM (
                'kaggle', 'devpost', 'devfolio', 'unstop', 'manual', 'other'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        "ALTER TABLE listings ALTER COLUMN source TYPE sourceplatform "
        "USING source::sourceplatform"
    )
