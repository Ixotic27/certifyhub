"""Add certificate events and attendee import linkage

Revision ID: b1d2c3e4f5a6
Revises: 9f2c1d6a3b7e
Create Date: 2026-02-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b1d2c3e4f5a6"
down_revision = "9f2c1d6a3b7e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "attendees",
        sa.Column("import_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        "fk_attendees_import_id",
        "attendees",
        "attendee_imports",
        ["import_id"],
        ["id"]
    )

    op.create_table(
        "certificate_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("club_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clubs.id"), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("certificate_templates.id"), nullable=False),
        sa.Column("import_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("attendee_imports.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="student"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"))
    )
    op.create_index("ix_certificate_events_club_id", "certificate_events", ["club_id"])
    op.create_index("ix_certificate_events_event_date", "certificate_events", ["event_date"])

    op.add_column(
        "certificate_generations",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        "fk_certificate_generations_event_id",
        "certificate_generations",
        "certificate_events",
        ["event_id"],
        ["id"]
    )


def downgrade():
    op.drop_index("ix_certificate_events_event_date", table_name="certificate_events")
    op.drop_index("ix_certificate_events_club_id", table_name="certificate_events")
    op.drop_table("certificate_events")
    op.drop_constraint("fk_certificate_generations_event_id", "certificate_generations", type_="foreignkey")
    op.drop_column("certificate_generations", "event_id")
    op.drop_constraint("fk_attendees_import_id", "attendees", type_="foreignkey")
    op.drop_column("attendees", "import_id")
