"""change tasks.user_id to BIGINT

Revision ID: c6b3d82e827a
Revises: c79dd41406f9
Create Date: 2025-06-14 01:22:33.380323

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6b3d82e827a'
down_revision: Union[str, None] = 'c79dd41406f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.alter_column('tasks', 'user_id',
               existing_type=sa.Integer(),
               type_=sa.BigInteger(),
               postgresql_using='user_id::bigint')

def downgrade():
    op.alter_column('tasks', 'user_id',
               existing_type=sa.BigInteger(),
               type_=sa.Integer(),
               postgresql_using='user_id::integer')