"""Scale infrastructure: WAL, ownership, event outbox, execution control, and indexes.

Revision ID: 002
Revises: 001
Create Date: 2026-10-26
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update execution_logs with owner_id, started_at, and compound indexes
    with op.batch_alter_table("execution_logs") as batch_op:
        batch_op.add_column(sa.Column("owner_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("started_at", sa.DateTime(), nullable=True))
        batch_op.create_index("ix_execution_logs_target_created", ["target_id", "created_at"])
        batch_op.create_index("ix_execution_logs_status_created", ["status", "created_at"])

    # 2. event_outbox
    op.create_table(
        "event_outbox",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_event_outbox_id", "event_outbox", ["id"])
    op.create_index("ix_event_outbox_created_at", "event_outbox", ["created_at"])

    # 3. process_heartbeat
    op.create_table(
        "process_heartbeat",
        sa.Column("owner_id", sa.String(), primary_key=True, nullable=False),
        sa.Column("pid", sa.Integer(), nullable=False),
        sa.Column("host", sa.String(), nullable=False),
        sa.Column("last_seen", sa.DateTime(), nullable=False),
    )

    # 4. execution_control
    op.create_table(
        "execution_control",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("execution_id", sa.String(), nullable=False),
        sa.Column("command", sa.String(), nullable=False),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("handled_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_execution_control_execution_id", "execution_control", ["execution_id"])

    # 5. distributed_lock
    op.create_table(
        "distributed_lock",
        sa.Column("name", sa.String(), primary_key=True, nullable=False),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("acquired_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("distributed_lock")
    op.drop_table("execution_control")
    op.drop_table("process_heartbeat")
    op.drop_table("event_outbox")

    with op.batch_alter_table("execution_logs") as batch_op:
        batch_op.drop_index("ix_execution_logs_status_created")
        batch_op.drop_index("ix_execution_logs_target_created")
        batch_op.drop_column("started_at")
        batch_op.drop_column("owner_id")
