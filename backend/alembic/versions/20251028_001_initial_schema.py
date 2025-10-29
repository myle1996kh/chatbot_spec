"""Initial schema with all 13 tables and seed data

Revision ID: 001
Revises:
Create Date: 2025-10-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all 13 tables and insert seed data."""

    # 1. Create tenants table
    op.create_table(
        'tenants',
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('domain', sa.String(255), unique=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now())
    )
    op.create_index('ix_tenants_status', 'tenants', ['status'])

    # 2. Create llm_models table
    op.create_table(
        'llm_models',
        sa.Column('llm_model_id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('context_window', sa.Integer, nullable=False),
        sa.Column('cost_per_1k_input_tokens', sa.DECIMAL(10, 6), nullable=False),
        sa.Column('cost_per_1k_output_tokens', sa.DECIMAL(10, 6), nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('capabilities', postgresql.JSONB),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now())
    )
    op.create_index('ix_llm_models_provider_model', 'llm_models', ['provider', 'model_name'])
    op.create_index('ix_llm_models_is_active', 'llm_models', ['is_active'])

    # 3. Create tenant_llm_configs table
    op.create_table(
        'tenant_llm_configs',
        sa.Column('config_id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('llm_model_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('encrypted_api_key', sa.Text, nullable=False),
        sa.Column('rate_limit_rpm', sa.Integer, server_default='60'),
        sa.Column('rate_limit_tpm', sa.Integer, server_default='10000'),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id']),
        sa.ForeignKeyConstraint(['llm_model_id'], ['llm_models.llm_model_id'])
    )
    op.create_index('ix_tenant_llm_configs_llm_model', 'tenant_llm_configs', ['llm_model_id'])

    # 4. Create base_tools table
    op.create_table(
        'base_tools',
        sa.Column('base_tool_id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('type', sa.String(50), nullable=False, unique=True),
        sa.Column('handler_class', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('default_config_schema', postgresql.JSONB),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now())
    )

    # 5. Create output_formats table
    op.create_table(
        'output_formats',
        sa.Column('format_id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('schema', postgresql.JSONB),
        sa.Column('renderer_hint', postgresql.JSONB),
        sa.Column('description', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now())
    )

    # 6. Create tool_configs table
    op.create_table(
        'tool_configs',
        sa.Column('tool_id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('base_tool_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('config', postgresql.JSONB, nullable=False),
        sa.Column('input_schema', postgresql.JSONB, nullable=False),
        sa.Column('output_format_id', postgresql.UUID(as_uuid=True)),
        sa.Column('description', sa.Text),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['base_tool_id'], ['base_tools.base_tool_id']),
        sa.ForeignKeyConstraint(['output_format_id'], ['output_formats.format_id'])
    )
    op.create_index('ix_tool_configs_base_tool', 'tool_configs', ['base_tool_id'])
    op.create_index('ix_tool_configs_is_active', 'tool_configs', ['is_active'])

    # 7. Create agent_configs table
    op.create_table(
        'agent_configs',
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('prompt_template', sa.Text, nullable=False),
        sa.Column('llm_model_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('default_output_format_id', postgresql.UUID(as_uuid=True)),
        sa.Column('description', sa.Text),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['llm_model_id'], ['llm_models.llm_model_id']),
        sa.ForeignKeyConstraint(['default_output_format_id'], ['output_formats.format_id'])
    )
    op.create_index('ix_agent_configs_is_active', 'agent_configs', ['is_active'])

    # 8. Create agent_tools junction table
    op.create_table(
        'agent_tools',
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tool_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('priority', sa.Integer, nullable=False),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('agent_id', 'tool_id'),
        sa.ForeignKeyConstraint(['agent_id'], ['agent_configs.agent_id']),
        sa.ForeignKeyConstraint(['tool_id'], ['tool_configs.tool_id'])
    )
    op.create_index('ix_agent_tools_agent_priority', 'agent_tools', ['agent_id', 'priority'])

    # 9. Create tenant_agent_permissions table
    op.create_table(
        'tenant_agent_permissions',
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('output_override_id', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('tenant_id', 'agent_id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id']),
        sa.ForeignKeyConstraint(['agent_id'], ['agent_configs.agent_id']),
        sa.ForeignKeyConstraint(['output_override_id'], ['output_formats.format_id'])
    )
    op.create_index('ix_tenant_agent_permissions_enabled', 'tenant_agent_permissions', ['enabled'])

    # 10. Create tenant_tool_permissions table
    op.create_table(
        'tenant_tool_permissions',
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tool_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('tenant_id', 'tool_id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id']),
        sa.ForeignKeyConstraint(['tool_id'], ['tool_configs.tool_id'])
    )
    op.create_index('ix_tenant_tool_permissions_enabled', 'tenant_tool_permissions', ['enabled'])

    # 11. Create sessions table
    op.create_table(
        'sessions',
        sa.Column('session_id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now()),
        sa.Column('last_message_at', sa.TIMESTAMP, nullable=False, server_default=sa.func.now()),
        sa.Column('metadata', postgresql.JSONB),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.tenant_id']),
        sa.ForeignKeyConstraint(['agent_id'], ['agent_configs.agent_id'])
    )
    op.create_index('ix_sessions_tenant_user', 'sessions', ['tenant_id', 'user_id', 'created_at'])
    op.create_index('ix_sessions_last_message', 'sessions', ['last_message_at'])

    # 12. Create messages table
    op.create_table(
        'messages',
        sa.Column('message_id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('timestamp', sa.TIMESTAMP, nullable=False, server_default=sa.func.now()),
        sa.Column('metadata', postgresql.JSONB),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.session_id'])
    )
    op.create_index('ix_messages_session_timestamp', 'messages', ['session_id', 'timestamp'])

    # 13. Create checkpoints table (for LangGraph PostgresSaver)
    op.create_table(
        'checkpoints',
        sa.Column('thread_id', sa.Text, primary_key=True),
        sa.Column('checkpoint_id', sa.Text, primary_key=True),
        sa.Column('parent_id', sa.Text),
        sa.Column('checkpoint', sa.LargeBinary, nullable=False),
        sa.Column('metadata', postgresql.JSONB)
    )


def downgrade() -> None:
    """Drop all tables in reverse order."""
    op.drop_table('checkpoints')
    op.drop_table('messages')
    op.drop_table('sessions')
    op.drop_table('tenant_tool_permissions')
    op.drop_table('tenant_agent_permissions')
    op.drop_table('agent_tools')
    op.drop_table('agent_configs')
    op.drop_table('tool_configs')
    op.drop_table('output_formats')
    op.drop_table('base_tools')
    op.drop_table('tenant_llm_configs')
    op.drop_table('llm_models')
    op.drop_table('tenants')
