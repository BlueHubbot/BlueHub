"""merge heads

Revision ID: bb19837c3368
Revises: 20260623_020930, 20260625_000100
Create Date: 2026-07-05 01:37:10.771733

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb19837c3368'
down_revision: Union[str, Sequence[str], None] = ('20260623_020930', '20260625_000100')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
