"""Add audience to templates and role to attendees

Revision ID: 4c8d9f7a1b2c
Revises: b7f2f1d9c9a2
Create Date: 2026-02-03
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "4c8d9f7a1b2c"
down_revision = "b7f2f1d9c9a2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "certificate_templates",
        sa.Column("audience", sa.String(20), nullable=False, server_default="student")
    )
    op.add_column(
        "attendees",
        sa.Column("role", sa.String(20), nullable=False, server_default="student")
    )


def downgrade():
    op.drop_column("attendees", "role")
    op.drop_column("certificate_templates", "audience")
