"""Enterprise Billing & Subscription Platform Database Migration

Revision ID: 003_billing
Revises: 002_multi_tenant
Create Date: 2026-07-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '003_billing'
down_revision = '002_multi_tenant'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Create payment_customers table
    op.create_table(
        'payment_customers',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(), server_default='stripe', nullable=False),
        sa.Column('provider_customer_id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pay_cust_org_id', 'payment_customers', ['organization_id'])
    op.create_index('ix_pay_cust_provider_cust_id', 'payment_customers', ['provider_customer_id'])

    # 2. Create payment_methods table
    op.create_table(
        'payment_methods',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('customer_id', sa.String(), sa.ForeignKey('payment_customers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(), server_default='stripe', nullable=False),
        sa.Column('provider_payment_method_id', sa.String(), nullable=False),
        sa.Column('type', sa.String(), server_default='card'),
        sa.Column('brand', sa.String(), nullable=True),
        sa.Column('last4', sa.String(), nullable=True),
        sa.Column('exp_month', sa.Integer(), nullable=True),
        sa.Column('exp_year', sa.Integer(), nullable=True),
        sa.Column('is_default', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pay_methods_cust_id', 'payment_methods', ['customer_id'])

    # 3. Create subscription_history table
    op.create_table(
        'subscription_history',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('subscription_id', sa.String(), sa.ForeignKey('subscriptions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('organization_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan_id', sa.String(), sa.ForeignKey('subscription_plans.id'), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('previous_plan_id', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sub_hist_sub_id', 'subscription_history', ['subscription_id'])
    op.create_index('ix_sub_hist_org_id', 'subscription_history', ['organization_id'])

    # 4. Create invoices table
    op.create_table(
        'invoices',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('invoice_number', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), server_default='internal'),
        sa.Column('provider_invoice_id', sa.String(), nullable=True),
        sa.Column('amount_due', sa.Float(), server_default='0.0'),
        sa.Column('amount_paid', sa.Float(), server_default='0.0'),
        sa.Column('currency', sa.String(), server_default='USD'),
        sa.Column('status', sa.String(), server_default='paid'),
        sa.Column('tax_amount', sa.Float(), server_default='0.0'),
        sa.Column('pdf_url', sa.String(), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('invoice_number')
    )
    op.create_index('ix_invoices_org_id', 'invoices', ['organization_id'])

    # 5. Create invoice_items table
    op.create_table(
        'invoice_items',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('invoice_id', sa.String(), sa.ForeignKey('invoices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('quantity', sa.Integer(), server_default='1'),
        sa.Column('unit_amount', sa.Float(), server_default='0.0'),
        sa.Column('amount', sa.Float(), server_default='0.0'),
        sa.Column('currency', sa.String(), server_default='USD'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_invoice_items_inv_id', 'invoice_items', ['invoice_id'])

    # 6. Create payments table
    op.create_table(
        'payments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('invoice_id', sa.String(), sa.ForeignKey('invoices.id', ondelete='SET NULL'), nullable=True),
        sa.Column('provider', sa.String(), server_default='stripe'),
        sa.Column('provider_payment_id', sa.String(), nullable=False),
        sa.Column('amount', sa.Float(), server_default='0.0'),
        sa.Column('currency', sa.String(), server_default='USD'),
        sa.Column('status', sa.String(), server_default='succeeded'),
        sa.Column('idempotency_key', sa.String(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key')
    )
    op.create_index('ix_payments_org_id', 'payments', ['organization_id'])
    op.create_index('ix_payments_provider_pay_id', 'payments', ['provider_payment_id'])

    # 7. Create refunds table
    op.create_table(
        'refunds',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('payment_id', sa.String(), sa.ForeignKey('payments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('organization_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider_refund_id', sa.String(), nullable=False),
        sa.Column('amount', sa.Float(), server_default='0.0'),
        sa.Column('currency', sa.String(), server_default='USD'),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('status', sa.String(), server_default='succeeded'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # 8. Create coupon_codes table
    op.create_table(
        'coupon_codes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('discount_type', sa.String(), server_default='percentage'),
        sa.Column('discount_value', sa.Float(), server_default='10.0'),
        sa.Column('max_redemptions', sa.Integer(), server_default='100'),
        sa.Column('times_redeemed', sa.Integer(), server_default='0'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    # 9. Create discounts table
    op.create_table(
        'discounts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('coupon_id', sa.String(), sa.ForeignKey('coupon_codes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('applied_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # 10. Create billing_events table
    op.create_table(
        'billing_events',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), nullable=True),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('event_data', sa.JSON(), nullable=True),
        sa.Column('processed', sa.Boolean(), server_default='true'),
        sa.Column('error_log', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_billing_events_org_id', 'billing_events', ['organization_id'])

def downgrade() -> None:
    op.drop_table('billing_events')
    op.drop_table('discounts')
    op.drop_table('coupon_codes')
    op.drop_table('refunds')
    op.drop_table('payments')
    op.drop_table('invoice_items')
    op.drop_table('invoices')
    op.drop_table('subscription_history')
    op.drop_table('payment_methods')
    op.drop_table('payment_customers')
