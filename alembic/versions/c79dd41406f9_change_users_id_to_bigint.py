"""change users.id to BIGINT

Revision ID: c79dd41406f9
Revises: e5bd489acdf6
Create Date: 2025-06-14 00:55:29.503318

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c79dd41406f9'
down_revision: Union[str, None] = 'e5bd489acdf6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('users', 'id',
               existing_type=sa.Integer(),
               type_=sa.BigInteger(),
               postgresql_using='id::bigint')


def downgrade() -> None:
    op.alter_column('users', 'id',
               existing_type=sa.BigInteger(),
               type_=sa.Integer(),
               postgresql_using='id::integer')