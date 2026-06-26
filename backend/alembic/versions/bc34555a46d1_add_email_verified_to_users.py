"""add email_verified to users

Revision ID: bc34555a46d1
Revises: 
Create Date: 2026-06-26 22:05:49.595324

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bc34555a46d1'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')), schema='ecommerce')


def downgrade() -> None:
    op.drop_column('users', 'email_verified', schema='ecommerce')
