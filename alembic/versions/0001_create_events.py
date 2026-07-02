"""create events table

Revision ID: 0001
Revises:
Create Date: 2026-07-01

"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("user_id", sa.String(length=120), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_events_event_type", "events", ["event_type"])
    op.create_index("ix_events_source", "events", ["source"])
    op.create_index("ix_events_user_id", "events", ["user_id"])
    op.create_index(
        "ix_events_type_source_time",
        "events",
        ["event_type", "source", "ingested_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_events_type_source_time", table_name="events")
    op.drop_index("ix_events_user_id", table_name="events")
    op.drop_index("ix_events_source", table_name="events")
    op.drop_index("ix_events_event_type", table_name="events")
    op.drop_table("events")
