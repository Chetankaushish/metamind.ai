"""Enterprise Multi-Tenant SaaS Database Migration

Revision ID: 002_multi_tenant
Revises: 001_initial
Create Date: 2026-07-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '002_multi_tenant'
down_revision = '001_initial'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('domain', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index('ix_organizations_name', 'organizations', ['name'])

    # 2. Create organization_members table
    op.create_table(
        'organization_members',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(), server_default='Member'),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_org_members_org_id', 'organization_members', ['organization_id'])
    op.create_index('ix_org_members_user_id', 'organization_members', ['user_id'])

    # 3. Create organization_settings table
    op.create_table(
        'organization_settings',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('currency', sa.String(), server_default='USD'),
        sa.Column('timezone', sa.String(), server_default='America/New_York'),
        sa.Column('ai_opt_in', sa.Boolean(), server_default='true'),
        sa.Column('max_campaigns', sa.Integer(), server_default='50'),
        sa.Column('settings_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id')
    )

    # 4. Create workspaces table
    op.create_table(
        'workspaces',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('workspace_type', sa.String(), server_default='Marketing Team'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workspaces_org_id', 'workspaces', ['organization_id'])

    # 5. Create workspace_members table
    op.create_table(
        'workspace_members',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(), server_default='Workspace Admin'),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # 6. Create invitations table
    op.create_table(
        'invitations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', sa.String(), sa.ForeignKey('workspaces.id', ondelete='SET NULL'), nullable=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('role', sa.String(), server_default='Manager'),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('status', sa.String(), server_default='pending'),
        sa.Column('invited_by', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
    )

    # 7. Create subscription_plans table
    op.create_table(
        'subscription_plans',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('monthly_price', sa.Float(), server_default='0.0'),
        sa.Column('seats_included', sa.Integer(), server_default='5'),
        sa.Column('max_campaigns', sa.Integer(), server_default='100'),
        sa.Column('sync_frequency_minutes', sa.Integer(), server_default='15'),
        sa.Column('automation_limit', sa.Integer(), server_default='20'),
        sa.Column('ai_token_monthly_limit', sa.Integer(), server_default='1000000'),
        sa.Column('storage_gb', sa.Integer(), server_default='10'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # 8. Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan_id', sa.String(), sa.ForeignKey('subscription_plans.id'), nullable=False),
        sa.Column('status', sa.String(), server_default='active'),
        sa.Column('current_period_start', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id')
    )

    # 9. Create usage_metrics table
    op.create_table(
        'usage_metrics',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('metric_type', sa.String(), nullable=False),
        sa.Column('quantity', sa.Integer(), server_default='1'),
        sa.Column('period_start', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # 10. Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('organization_id', sa.String(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('key_hash', sa.String(), nullable=False),
        sa.Column('prefix', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash')
    )

def downgrade() -> None:
    op.drop_table('api_keys')
    op.drop_table('usage_metrics')
    op.drop_table('subscriptions')
    op.drop_table('subscription_plans')
    op.drop_table('invitations')
    op.drop_table('workspace_members')
    op.drop_table('workspaces')
    op.drop_table('organization_settings')
    op.drop_table('organization_members')
    op.drop_table('organizations')
