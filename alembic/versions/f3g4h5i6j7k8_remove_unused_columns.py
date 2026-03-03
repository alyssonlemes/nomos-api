"""remove unused columns data_ultima_movimentacao and tempo_tramitacao_dias

Revision ID: f3g4h5i6j7k8
Revises: e2f3g4h5i6j7
Create Date: 2026-03-02 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3g4h5i6j7k8"
down_revision: Union[str, None] = "e2f3g4h5i6j7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("jurimetria_dataset", "data_ultima_movimentacao")
    op.drop_column("jurimetria_dataset", "tempo_tramitacao_dias")


def downgrade() -> None:
    op.add_column(
        "jurimetria_dataset",
        sa.Column("tempo_tramitacao_dias", sa.Integer(), nullable=True),
    )
    op.add_column(
        "jurimetria_dataset",
        sa.Column("data_ultima_movimentacao", sa.Date(), nullable=True),
    )
