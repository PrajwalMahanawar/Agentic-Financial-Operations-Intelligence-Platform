from alembic import op
import sqlalchemy as sa

revision = "0001_initial_platform"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "investigation_cases",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("customer_id", sa.String(length=128), nullable=False),
        sa.Column("case_type", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_investigation_cases_customer_id", "investigation_cases", ["customer_id"])
    op.create_index("ix_investigation_cases_case_type", "investigation_cases", ["case_type"])
    op.create_index("ix_investigation_cases_status", "investigation_cases", ["status"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("actor", sa.String(length=256), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_actor", "audit_logs", ["actor"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])
    op.create_index("ix_audit_logs_resource_id", "audit_logs", ["resource_id"])

    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source", sa.String(length=256), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_knowledge_documents_source", "knowledge_documents", ["source"])


def downgrade() -> None:
    op.drop_table("knowledge_documents")
    op.drop_table("audit_logs")
    op.drop_table("investigation_cases")
