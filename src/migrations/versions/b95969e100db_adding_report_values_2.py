"""Adding report values 2

Revision ID: b95969e100db
Revises: bb844aded8ce
Create Date: 2025-04-08 01:32:00.279595

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b95969e100db'
down_revision: Union[str, None] = 'bb844aded8ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_token_blacklist_token', table_name='token_blacklist')
    op.drop_table('token_blacklist')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('token_blacklist',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('token', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('expires_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name='token_blacklist_pkey')
    )
    op.create_index('ix_token_blacklist_token', 'token_blacklist', ['token'], unique=True)
    # ### end Alembic commands ###
