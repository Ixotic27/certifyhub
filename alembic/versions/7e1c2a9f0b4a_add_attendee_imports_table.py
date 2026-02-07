"""Add attendee imports table

Revision ID: 7e1c2a9f0b4a
Revises: 4c8d9f7a1b2c
Create Date: 2026-02-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "7e1c2a9f0b4a"
down_revision = "4c8d9f7a1b2c"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "attendee_imports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("club_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clubs.id"), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="student"),
        sa.Column("rows_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uploaded_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False)
    )
    op.create_index("ix_attendee_imports_club_id", "attendee_imports", ["club_id"])


def downgrade():
    op.drop_index("ix_attendee_imports_club_id", table_name="attendee_imports")
    op.drop_table("attendee_imports")
