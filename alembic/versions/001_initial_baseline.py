"""Initial baseline matching Phase 1-3 database schema.

Revision ID: 001
Revises: None
Create Date: 2026-10-26
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. plugin_profiles
    op.create_table(
        "plugin_profiles",
        sa.Column("id", sa.String(), nullable=False, primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("driver", sa.String(), nullable=False),
        sa.Column("entrypoint", sa.String(), nullable=False),
        sa.Column("dry_run_command", sa.String(), nullable=False, server_default="SET SHOWPLAN_XML ON"),
        sa.Column("abort_command", sa.String(), nullable=False, server_default="KILL {spid}"),
        sa.Column("config_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("ui_schema_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("custom_card_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("active_sessions_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_certified", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("certification_report_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_plugin_profiles_id", "plugin_profiles", ["id"])

    # 2. knowledge_chunks
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.String(), nullable=False, primary_key=True),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.Column("partition_key", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("catalog_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("doc_markdown", sa.Text(), nullable=False, server_default=""),
        sa.Column("skills_markdown", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_knowledge_chunks_id", "knowledge_chunks", ["id"])
    op.create_index("ix_knowledge_chunks_target_id", "knowledge_chunks", ["target_id"])
    op.create_index("ix_knowledge_chunks_partition_key", "knowledge_chunks", ["partition_key"])

    # 3. governance_rules
    op.create_table(
        "governance_rules",
        sa.Column("id", sa.String(), nullable=False, primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("target_id", sa.String(), nullable=True),
        sa.Column("rule_type", sa.String(), nullable=False),
        sa.Column("expression", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("severity", sa.String(), nullable=False, server_default="HIGH"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_governance_rules_id", "governance_rules", ["id"])
    op.create_index("ix_governance_rules_target_id", "governance_rules", ["target_id"])

    # 4. execution_logs
    op.create_table(
        "execution_logs",
        sa.Column("id", sa.String(), nullable=False, primary_key=True),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("query_type", sa.String(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column("explain_plan_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("violations_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("execution_time_ms", sa.Float(), nullable=True),
        sa.Column("auto_approved", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("spid", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_execution_logs_id", "execution_logs", ["id"])
    op.create_index("ix_execution_logs_target_id", "execution_logs", ["target_id"])
    op.create_index("ix_execution_logs_status", "execution_logs", ["status"])
    op.create_index("ix_execution_logs_created_at", "execution_logs", ["created_at"])

    # 5. system_settings
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(), nullable=False, primary_key=True),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("system_settings")
    op.drop_table("execution_logs")
    op.drop_table("governance_rules")
    op.drop_table("knowledge_chunks")
    op.drop_table("plugin_profiles")
