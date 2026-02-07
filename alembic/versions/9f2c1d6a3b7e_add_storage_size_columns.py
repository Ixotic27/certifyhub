"""Add storage size tracking

Revision ID: 9f2c1d6a3b7e
Revises: 7e1c2a9f0b4a
Create Date: 2026-02-05
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "9f2c1d6a3b7e"
down_revision = "7e1c2a9f0b4a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("certificate_templates", sa.Column("image_size_bytes", sa.BigInteger(), server_default="0", nullable=False))
    op.add_column("attendee_imports", sa.Column("file_size_bytes", sa.BigInteger(), server_default="0", nullable=False))


def downgrade():
    op.drop_column("attendee_imports", "file_size_bytes")
    op.drop_column("certificate_templates", "image_size_bytes")
