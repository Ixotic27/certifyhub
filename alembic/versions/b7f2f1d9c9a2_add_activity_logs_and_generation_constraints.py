"""Add activity logs and certificate generation constraints

Revision ID: b7f2f1d9c9a2
Revises: 180e46c592d8
Create Date: 2026-02-03
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b7f2f1d9c9a2"
down_revision = "180e46c592d8"
branch_labels = None
depends_on = None


def upgrade():
    # Create activity_logs table
    op.create_table(
        "activity_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("club_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["clubs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["admin_id"], ["club_administrators.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_activity_logs_club_id", "activity_logs", ["club_id"])
    op.create_index("ix_activity_logs_admin_id", "activity_logs", ["admin_id"])
    op.create_index("ix_activity_logs_action", "activity_logs", ["action"])

    # Add unique index for one generation per attendee/template/day
    # Note: Removed due to PostgreSQL IMMUTABLE requirement
    # We'll rely on application-level logic to prevent duplicate generations

    # Trigger to update attendee counts after generation
    op.execute(
        """
        CREATE OR REPLACE FUNCTION update_certificate_count()
        RETURNS TRIGGER AS $$
        BEGIN
            UPDATE attendees
            SET
                certificate_generated_count = COALESCE(certificate_generated_count, 0) + 1,
                first_generated_at = COALESCE(first_generated_at, NEW.generated_at),
                last_generated_at = NEW.generated_at
            WHERE id = NEW.attendee_id;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER track_certificate_generation
            AFTER INSERT ON certificate_generations
            FOR EACH ROW EXECUTE FUNCTION update_certificate_count();
        """
    )

    # Trigger to log template uploads
    op.execute(
        """
        CREATE OR REPLACE FUNCTION log_admin_activity()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_TABLE_NAME = 'certificate_templates' AND TG_OP = 'INSERT' THEN
                INSERT INTO activity_logs (id, club_id, admin_id, action, resource_type, resource_id)
                VALUES (gen_random_uuid(), NEW.club_id, NEW.created_by, 'upload_template', 'template', NEW.id);
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER log_template_upload
            AFTER INSERT ON certificate_templates
            FOR EACH ROW EXECUTE FUNCTION log_admin_activity();
        """
    )


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS log_template_upload ON certificate_templates;")
    op.execute("DROP FUNCTION IF EXISTS log_admin_activity;")

    op.execute("DROP TRIGGER IF EXISTS track_certificate_generation ON certificate_generations;")
    op.execute("DROP FUNCTION IF EXISTS update_certificate_count;")

    op.execute(
        "DROP INDEX IF EXISTS uq_certificate_generations_attendee_template_day;"
    )

    op.drop_index("ix_activity_logs_action", table_name="activity_logs")
    op.drop_index("ix_activity_logs_admin_id", table_name="activity_logs")
    op.drop_index("ix_activity_logs_club_id", table_name="activity_logs")
    op.drop_table("activity_logs")
