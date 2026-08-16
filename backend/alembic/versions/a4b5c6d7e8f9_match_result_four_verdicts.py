"""match_results add missing_params/match_reason/risk_warning (D10 四档 + D4 解释)

Revision ID: a4b5c6d7e8f9
Revises: d3f0c1a2b9e7
Create Date: 2026-08-16 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a4b5c6d7e8f9'
down_revision: Union[str, None] = 'd3f0c1a2b9e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # D10：missing 独立成组（不再并入 partial）
    op.add_column('match_results', sa.Column('missing_params', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    # D4：顾问级解释（match_reason + risk_warning）
    op.add_column('match_results', sa.Column('match_reason', sa.Text(), nullable=True))
    op.add_column('match_results', sa.Column('risk_warning', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('match_results', 'risk_warning')
    op.drop_column('match_results', 'match_reason')
    op.drop_column('match_results', 'missing_params')
