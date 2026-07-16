"""add offers, offer_qualifying_products, offer_redemptions tables

Revision ID: a1b2c3d4e5f6
Revises: bc34555a46d1
Create Date: 2026-07-15 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'bc34555a46d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # offers
    op.create_table(
        'offers',
        sa.Column('offer_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('offer_name', sa.String(100), nullable=False),
        sa.Column('criteria_type', sa.String(20), nullable=False),
        sa.Column('product_scope', sa.String(20), nullable=False),
        sa.Column('product_id', sa.Integer, nullable=True),
        sa.Column('required_count', sa.Integer, nullable=True),
        sa.Column('required_value', sa.Numeric(10, 2), nullable=True),
        sa.Column('reward_type', sa.String(20), nullable=False),
        sa.Column('free_product_id', sa.Integer, nullable=True),
        sa.Column('free_product_qty', sa.Integer, nullable=True),
        sa.Column('discount_percentage', sa.Numeric(5, 2), nullable=True),
        sa.Column('start_datetime', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_datetime', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(10), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "end_datetime > start_datetime",
            name="ck_offers_end_after_start",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_offers_status_enum",
        ),
        sa.CheckConstraint(
            "criteria_type IN ('PURCHASE_COUNT', 'PURCHASE_VALUE')",
            name="ck_offers_criteria_type_enum",
        ),
        sa.CheckConstraint(
            "product_scope IN ('SINGLE_PRODUCT', 'MULTIPLE_PRODUCT')",
            name="ck_offers_product_scope_enum",
        ),
        sa.CheckConstraint(
            "reward_type IN ('FREE_PRODUCT', 'PRICE_DISCOUNT')",
            name="ck_offers_reward_type_enum",
        ),
        schema='ecommerce',
    )
    op.create_index('ix_offers_status', 'offers', ['status'], schema='ecommerce')
    op.create_index('ix_offers_dates', 'offers', ['start_datetime', 'end_datetime'], schema='ecommerce')

    # offer_qualifying_products
    op.create_table(
        'offer_qualifying_products',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('offer_id', UUID(as_uuid=True),
                  sa.ForeignKey('ecommerce.offers.offer_id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('product_id', sa.Integer, nullable=False),
        sa.UniqueConstraint('offer_id', 'product_id', name='uq_offer_qualifying_product'),
        schema='ecommerce',
    )

    # offer_redemptions
    op.create_table(
        'offer_redemptions',
        sa.Column('redemption_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('offer_id', UUID(as_uuid=True),
                  sa.ForeignKey('ecommerce.offers.offer_id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('customer_id', UUID(as_uuid=True),
                  sa.ForeignKey('ecommerce.customer_info.id', ondelete='SET NULL'),
                  nullable=True),
        sa.Column('order_id', UUID(as_uuid=True),
                  sa.ForeignKey('ecommerce.orders.id', ondelete='SET NULL'),
                  nullable=True),
        sa.Column('redeemed_at', sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column('benefit_applied', sa.JSON, nullable=True),
        schema='ecommerce',
    )
    op.create_index('ix_offer_redemptions_customer', 'offer_redemptions', ['customer_id'], schema='ecommerce')


def downgrade() -> None:
    op.drop_index('ix_offer_redemptions_customer', table_name='offer_redemptions', schema='ecommerce')
    op.drop_table('offer_redemptions', schema='ecommerce')
    op.drop_table('offer_qualifying_products', schema='ecommerce')
    op.drop_index('ix_offers_dates', table_name='offers', schema='ecommerce')
    op.drop_index('ix_offers_status', table_name='offers', schema='ecommerce')
    op.drop_table('offers', schema='ecommerce')
