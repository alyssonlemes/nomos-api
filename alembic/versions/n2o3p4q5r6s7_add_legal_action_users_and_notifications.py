"""add legal_action_users and notifications

Revision ID: n2o3p4q5r6s7
Revises: m1n2o3p4q5r6
Create Date: 2026-05-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "n2o3p4q5r6s7"
down_revision: Union[str, None] = "m1n2o3p4q5r6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "legal_action_users" not in existing_tables:
        op.create_table(
            "legal_action_users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("legal_action_id", sa.Integer(), sa.ForeignKey("legal_actions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.UniqueConstraint("legal_action_id", "user_id", name="uq_legal_action_user"),
        )
        op.create_index("idx_legal_action_user_action", "legal_action_users", ["legal_action_id"], unique=False)
        op.create_index("idx_legal_action_user_user", "legal_action_users", ["user_id"], unique=False)

    if "notifications" not in existing_tables:
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("legal_action_id", sa.Integer(), sa.ForeignKey("legal_actions.id", ondelete="SET NULL"), nullable=True),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("message", sa.String(), nullable=False),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        )
        op.create_index("idx_notifications_user", "notifications", ["user_id"], unique=False)
        op.create_index("idx_notifications_read", "notifications", ["read_at"], unique=False)

    op.execute(
        """
        INSERT INTO legal_action_users (legal_action_id, user_id, created_at)
        SELECT id, user_id, COALESCE(created_at, CURRENT_TIMESTAMP)
        FROM legal_actions
        WHERE user_id IS NOT NULL
          AND NOT EXISTS (
            SELECT 1
            FROM legal_action_users lau
            WHERE lau.legal_action_id = legal_actions.id
              AND lau.user_id = legal_actions.user_id
          )
        """
    )


def downgrade() -> None:
    op.drop_index("idx_notifications_read", table_name="notifications")
    op.drop_index("idx_notifications_user", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("idx_legal_action_user_user", table_name="legal_action_users")
    op.drop_index("idx_legal_action_user_action", table_name="legal_action_users")
    op.drop_table("legal_action_users")
