"""Phase 0 teammate finding: interest signals + team channel URLs.

Revision ID: 20260808_0001
Revises:
Create Date: 2026-08-08
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260808_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("team_channel_url", sa.String(), nullable=True))
    op.add_column(
        "user_profiles",
        sa.Column("looking_for_team", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column("user_profiles", sa.Column("team_needs", sa.JSON(), nullable=True))
    op.create_table(
        "listing_interests",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("listing_id", sa.String(), sa.ForeignKey("listings.id"), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("profile_id", sa.String(), sa.ForeignKey("user_profiles.id"), nullable=True),
        sa.Column("team_needs", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email", "listing_id", name="uq_interest_email_listing"),
    )
    op.create_index("ix_listing_interests_listing_id", "listing_interests", ["listing_id"])
    op.create_index("ix_listing_interests_email", "listing_interests", ["email"])
    op.create_index("ix_listing_interests_profile_id", "listing_interests", ["profile_id"])
    op.create_index("ix_user_profiles_looking_for_team", "user_profiles", ["looking_for_team"])


def downgrade() -> None:
    op.drop_index("ix_user_profiles_looking_for_team", table_name="user_profiles")
    op.drop_index("ix_listing_interests_profile_id", table_name="listing_interests")
    op.drop_index("ix_listing_interests_email", table_name="listing_interests")
    op.drop_index("ix_listing_interests_listing_id", table_name="listing_interests")
    op.drop_table("listing_interests")
    op.drop_column("user_profiles", "team_needs")
    op.drop_column("user_profiles", "looking_for_team")
    op.drop_column("listings", "team_channel_url")
