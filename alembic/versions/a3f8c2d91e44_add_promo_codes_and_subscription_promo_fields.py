"""Add promo_codes table and promo fields to subscriptions

Revision ID: a3f8c2d91e44
Revises: 21dd559b8975
Create Date: 2026-05-30 00:00:00.000000

Changes:
  - New table: promo_codes
  - subscriptions: add promo_code (str), discount_amount (float) columns
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f8c2d91e44'
down_revision: Union[str, None] = '21dd559b8975'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── promo_codes table ──────────────────────────────────────────────────────
    op.create_table(
        'promo_codes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('description', sa.String(300), nullable=True),
        sa.Column(
            'discount_type',
            sa.Enum('percent', 'fixed', 'free_trial', name='discounttype'),
            nullable=False,
        ),
        sa.Column('discount_value', sa.Float(), nullable=False),
        sa.Column('max_uses', sa.Integer(), nullable=True),
        sa.Column('used_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_index('ix_promo_codes_code', 'promo_codes', ['code'], unique=True)

    # ── subscriptions: add promo columns ──────────────────────────────────────
    op.add_column(
        'subscriptions',
        sa.Column('promo_code', sa.String(50), nullable=True),
    )
    op.add_column(
        'subscriptions',
        sa.Column('discount_amount', sa.Float(), nullable=True, server_default='0'),
    )

    # ── Seed FIRST100 promo code ───────────────────────────────────────────────
    op.execute("""
        INSERT INTO promo_codes
            (id, code, description, discount_type, discount_value,
             max_uses, used_count, is_active, is_public, expires_at, created_at, updated_at)
        VALUES
            (
                gen_random_uuid()::text,
                'FIRST100',
                'First 100 doctors get 3 months free! Limited offer.',
                'free_trial',
                90,
                100,
                0,
                true,
                true,
                NULL,
                NOW(),
                NOW()
            )
    """)


def downgrade() -> None:
    op.drop_column('subscriptions', 'discount_amount')
    op.drop_column('subscriptions', 'promo_code')
    op.drop_index('ix_promo_codes_code', table_name='promo_codes')
    op.drop_table('promo_codes')
    op.execute("DROP TYPE IF EXISTS discounttype")
