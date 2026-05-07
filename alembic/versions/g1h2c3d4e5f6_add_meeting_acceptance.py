"""add meeting acceptance

Revision ID: g1h2c3d4e5f6
Revises: f3g4h5i6j7k8
Create Date: 2026-05-06 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'g1h2c3d4e5f6'
down_revision = 'f3g4h5i6j7k8'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to meetings
    op.add_column('meetings', sa.Column('requires_acceptance', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('meetings', sa.Column('status', sa.String(length=32), nullable=False, server_default=sa.text("'scheduled'")))

    # Recreate meeting_participants table to include metadata (id, status, accepted_at, reason, responded_by_id, invite_token)
    op.create_table(
        'meeting_participants_new',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default=sa.text("'pending'")),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('responded_by_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('invite_token', sa.String(length=128), nullable=True),
    )

    # Copy existing participant links into the new table. Existing rows will be marked as 'accepted' to preserve current behavior.
    op.execute(
        "INSERT INTO meeting_participants_new (meeting_id, user_id, status) SELECT meeting_id, user_id, 'accepted' FROM meeting_participants"
    )

    # Drop old table and rename new
    op.drop_table('meeting_participants')
    op.rename_table('meeting_participants_new', 'meeting_participants')


def downgrade():
    # Recreate old simple meeting_participants table (meeting_id, user_id)
    op.create_table(
        'meeting_participants_old',
        sa.Column('meeting_id', sa.Integer(), sa.ForeignKey('meetings.id', ondelete='CASCADE'), primary_key=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True, nullable=False),
    )

    # Copy back meeting_id,user_id
    op.execute(
        "INSERT INTO meeting_participants_old (meeting_id, user_id) SELECT meeting_id, user_id FROM meeting_participants"
    )

    # Drop enhanced table and rename old back
    op.drop_table('meeting_participants')
    op.rename_table('meeting_participants_old', 'meeting_participants')

    # Remove added columns from meetings
    op.drop_column('meetings', 'status')
    op.drop_column('meetings', 'requires_acceptance')
