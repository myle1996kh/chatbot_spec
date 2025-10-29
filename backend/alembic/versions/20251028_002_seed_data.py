"""Seed data for base_tools, output_formats, and llm_models

Revision ID: 002
Revises: 001
Create Date: 2025-10-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Insert seed data."""

    # Generate UUIDs for seed data
    http_get_id = str(uuid.uuid4())
    http_post_id = str(uuid.uuid4())
    rag_id = str(uuid.uuid4())
    db_query_id = str(uuid.uuid4())
    ocr_id = str(uuid.uuid4())

    structured_json_id = str(uuid.uuid4())
    markdown_table_id = str(uuid.uuid4())
    chart_data_id = str(uuid.uuid4())
    summary_text_id = str(uuid.uuid4())

    gpt4o_mini_id = str(uuid.uuid4())
    gpt4o_id = str(uuid.uuid4())
    gemini_id = str(uuid.uuid4())
    claude_id = str(uuid.uuid4())

    # Insert base_tools seed data
    op.execute(
        f"""
        INSERT INTO base_tools (base_tool_id, type, handler_class, description) VALUES
        ('{http_get_id}', 'HTTP_GET', 'tools.http.HTTPGetTool', 'HTTP GET request tool'),
        ('{http_post_id}', 'HTTP_POST', 'tools.http.HTTPPostTool', 'HTTP POST request tool'),
        ('{rag_id}', 'RAG', 'tools.rag.RAGTool', 'RAG vector search tool'),
        ('{db_query_id}', 'DB_QUERY', 'tools.db.DBQueryTool', 'Database query tool'),
        ('{ocr_id}', 'OCR', 'tools.ocr.OCRTool', 'OCR document processing tool')
        """
    )

    # Insert output_formats seed data
    op.execute(
        f"""
        INSERT INTO output_formats (format_id, name, schema, renderer_hint, description) VALUES
        (
            '{structured_json_id}',
            'structured_json',
            '{{"type": "object"}}'::jsonb,
            '{{"type": "json"}}'::jsonb,
            'Structured JSON output format'
        ),
        (
            '{markdown_table_id}',
            'markdown_table',
            '{{"type": "string"}}'::jsonb,
            '{{"type": "table"}}'::jsonb,
            'Markdown table output format'
        ),
        (
            '{chart_data_id}',
            'chart_data',
            '{{"type": "object"}}'::jsonb,
            '{{"type": "chart", "chartType": "bar"}}'::jsonb,
            'Chart data output format'
        ),
        (
            '{summary_text_id}',
            'summary_text',
            '{{"type": "string"}}'::jsonb,
            '{{"type": "text"}}'::jsonb,
            'Summary text output format'
        )
        """
    )

    # Insert llm_models seed data
    op.execute(
        f"""
        INSERT INTO llm_models (
            llm_model_id, provider, model_name, context_window,
            cost_per_1k_input_tokens, cost_per_1k_output_tokens, is_active
        ) VALUES
        ('{gpt4o_mini_id}', 'openai', 'gpt-4o-mini', 128000, 0.00015, 0.0006, true),
        ('{gpt4o_id}', 'openai', 'gpt-4o', 128000, 0.0025, 0.01, true),
        ('{gemini_id}', 'gemini', 'gemini-1.5-pro', 1048576, 0.00125, 0.00375, true),
        ('{claude_id}', 'anthropic', 'claude-3-5-sonnet-20241022', 200000, 0.003, 0.015, true)
        """
    )


def downgrade() -> None:
    """Remove seed data."""
    op.execute("DELETE FROM llm_models")
    op.execute("DELETE FROM output_formats")
    op.execute("DELETE FROM base_tools")
