"""Create all initial tables"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '180e46c592d8'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create clubs table
    op.create_table(
        'clubs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(50), nullable=False),
        sa.Column('contact_email', sa.String(255), nullable=False),
        sa.Column('logo_url', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_clubs_slug'), 'clubs', ['slug'])

    # Create platform_admins table
    op.create_table(
        'platform_admins',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('must_change_password', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_platform_admins_email'), 'platform_admins', ['email'])

    # Create club_administrators table
    op.create_table(
        'club_administrators',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('club_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('must_change_password', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['club_id'], ['clubs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_club_administrators_email'), 'club_administrators', ['email'])

    # Create certificate_templates table
    op.create_table(
        'certificate_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('club_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('event_name', sa.String(200), nullable=True),
        sa.Column('template_image_url', sa.Text(), nullable=False),
        sa.Column('text_fields', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('version', sa.Integer(), server_default='1'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['club_id'], ['clubs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['club_administrators.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # Create attendees table
    op.create_table(
        'attendees',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('club_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('student_id', sa.String(50), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('course', sa.String(100), nullable=True),
        sa.Column('event_name', sa.String(200), nullable=True),
        sa.Column('event_date', sa.Date(), nullable=True),
        sa.Column('certificate_generated_count', sa.Integer(), server_default='0'),
        sa.Column('first_generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['club_id'], ['clubs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['certificate_templates.id']),
        sa.ForeignKeyConstraint(['uploaded_by'], ['club_administrators.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_attendees_name'), 'attendees', ['name'])
    op.create_index(op.f('ix_attendees_student_id'), 'attendees', ['student_id'])

    # Create certificate_generations table
    op.create_table(
        'certificate_generations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('club_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('attendee_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('certificate_id', sa.String(100), nullable=False),
        sa.Column('generated_by_user', sa.String(10), server_default='public'),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['club_id'], ['clubs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['attendee_id'], ['attendees.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['certificate_templates.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_certificate_generations_certificate_id'), 'certificate_generations', ['certificate_id'])


def downgrade():
    op.drop_index(op.f('ix_certificate_generations_certificate_id'), table_name='certificate_generations')
    op.drop_table('certificate_generations')
    op.drop_index(op.f('ix_attendees_student_id'), table_name='attendees')
    op.drop_index(op.f('ix_attendees_name'), table_name='attendees')
    op.drop_table('attendees')
    op.drop_table('certificate_templates')
    op.drop_index(op.f('ix_club_administrators_email'), table_name='club_administrators')
    op.drop_table('club_administrators')
    op.drop_index(op.f('ix_platform_admins_email'), table_name='platform_admins')
    op.drop_table('platform_admins')
    op.drop_index(op.f('ix_clubs_slug'), table_name='clubs')
    op.drop_table('clubs')
