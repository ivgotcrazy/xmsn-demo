"""vendor_capabilities add soft_tags (D3 软层自由标签)

Revision ID: d3f0c1a2b9e7
Revises: 0176a45f1dbb
Create Date: 2026-08-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd3f0c1a2b9e7'
down_revision: Union[str, None] = '0176a45f1dbb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # D3 软层：本体外自由能力标签（与 structured_tags 分离，不参与硬判定）
    op.add_column('vendor_capabilities', sa.Column('soft_tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('vendor_capabilities', 'soft_tags')
