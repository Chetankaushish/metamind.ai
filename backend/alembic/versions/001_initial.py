"""Initial PostgreSQL Schema for MetaMind AI

Revision ID: 001_initial
Revises: 
Create Date: 2026-07-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('role', sa.String(), nullable=True, server_default='Admin'),
        sa.Column('company_name', sa.String(), nullable=True),
        sa.Column('plan', sa.String(), nullable=True, server_default='Enterprise'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    op.create_table(
        'meta_accounts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('meta_user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('connection_status', sa.String(), server_default='connected'),
        sa.Column('last_connected', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('meta_user_id')
    )

    op.create_table(
        'oauth_tokens',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('meta_account_id', sa.String(), sa.ForeignKey('meta_accounts.id'), nullable=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('encrypted_access_token', sa.Text(), nullable=False),
        sa.Column('token_type', sa.String(), server_default='long_lived_user'),
        sa.Column('scopes', sa.JSON(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_refreshed', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('is_valid', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'business_managers',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('bm_meta_id', sa.String(), nullable=False),
        sa.Column('meta_account_id', sa.String(), sa.ForeignKey('meta_accounts.id'), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('verification_status', sa.String(), server_default='verified'),
        sa.Column('ad_accounts_count', sa.Integer(), server_default='1'),
        sa.Column('is_primary', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('bm_meta_id')
    )

    op.create_table(
        'ad_accounts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('account_name', sa.String(), nullable=False),
        sa.Column('account_id', sa.String(), nullable=False),
        sa.Column('meta_account_id', sa.String(), sa.ForeignKey('meta_accounts.id'), nullable=True),
        sa.Column('business_manager_id', sa.String(), sa.ForeignKey('business_managers.id'), nullable=True),
        sa.Column('currency', sa.String(), server_default='USD'),
        sa.Column('timezone', sa.String(), server_default='America/New_York'),
        sa.Column('spend_limit', sa.Float(), server_default='250000.0'),
        sa.Column('amount_spent', sa.Float(), server_default='0.0'),
        sa.Column('status', sa.String(), server_default='active'),
        sa.Column('pixel_id', sa.String(), nullable=True),
        sa.Column('pixel_health', sa.String(), server_default='optimal'),
        sa.Column('capi_health', sa.String(), server_default='optimal'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('account_id')
    )

    op.create_table(
        'campaigns',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('campaign_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('ad_account_id', sa.String(), sa.ForeignKey('ad_accounts.id'), nullable=True),
        sa.Column('status', sa.String(), server_default='ACTIVE'),
        sa.Column('objective', sa.String(), server_default='OUTCOME_SALES'),
        sa.Column('buying_type', sa.String(), server_default='AUCTION'),
        sa.Column('daily_budget', sa.Float(), server_default='0.0'),
        sa.Column('lifetime_budget', sa.Float(), server_default='0.0'),
        sa.Column('spend', sa.Float(), server_default='0.0'),
        sa.Column('revenue', sa.Float(), server_default='0.0'),
        sa.Column('roas', sa.Float(), server_default='0.0'),
        sa.Column('ctr', sa.Float(), server_default='0.0'),
        sa.Column('cpm', sa.Float(), server_default='0.0'),
        sa.Column('cpc', sa.Float(), server_default='0.0'),
        sa.Column('cpa', sa.Float(), server_default='0.0'),
        sa.Column('purchases', sa.Integer(), server_default='0'),
        sa.Column('clicks', sa.Integer(), server_default='0'),
        sa.Column('impressions', sa.Integer(), server_default='0'),
        sa.Column('reach', sa.Integer(), server_default='0'),
        sa.Column('learning_phase', sa.String(), server_default='learning'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('campaign_id')
    )

    op.create_table(
        'ad_sets',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('ad_set_id', sa.String(), nullable=False),
        sa.Column('campaign_id', sa.String(), sa.ForeignKey('campaigns.id'), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('status', sa.String(), server_default='ACTIVE'),
        sa.Column('daily_budget', sa.Float(), server_default='0.0'),
        sa.Column('bid_strategy', sa.String(), server_default='LOWEST_COST_WITHOUT_CAP'),
        sa.Column('optimization_goal', sa.String(), server_default='OFFSITE_CONVERSIONS'),
        sa.Column('target_audience', sa.String(), nullable=True),
        sa.Column('cpa', sa.Float(), server_default='0.0'),
        sa.Column('roas', sa.Float(), server_default='0.0'),
        sa.Column('spend', sa.Float(), server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ad_set_id')
    )

    op.create_table(
        'ads',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('ad_id', sa.String(), nullable=False),
        sa.Column('ad_set_id', sa.String(), sa.ForeignKey('ad_sets.id'), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('status', sa.String(), server_default='ACTIVE'),
        sa.Column('format', sa.String(), server_default='Video'),
        sa.Column('creative_title', sa.String(), nullable=True),
        sa.Column('creative_body', sa.Text(), nullable=True),
        sa.Column('media_url', sa.String(), nullable=True),
        sa.Column('ctr', sa.Float(), server_default='0.0'),
        sa.Column('cpc', sa.Float(), server_default='0.0'),
        sa.Column('spend', sa.Float(), server_default='0.0'),
        sa.Column('fatigue_level', sa.String(), server_default='Low'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ad_id')
    )

    op.create_table(
        'creatives',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('creative_id', sa.String(), nullable=False),
        sa.Column('ad_account_id', sa.String(), sa.ForeignKey('ad_accounts.id'), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('image_url', sa.String(), nullable=True),
        sa.Column('video_url', sa.String(), nullable=True),
        sa.Column('call_to_action', sa.String(), server_default='LEARN_MORE'),
        sa.Column('object_type', sa.String(), server_default='SHARE'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('creative_id')
    )

    op.create_table(
        'insights',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('campaign_id', sa.String(), sa.ForeignKey('campaigns.id'), nullable=True),
        sa.Column('ad_set_id', sa.String(), sa.ForeignKey('ad_sets.id'), nullable=True),
        sa.Column('ad_id', sa.String(), sa.ForeignKey('ads.id'), nullable=True),
        sa.Column('ad_account_id', sa.String(), sa.ForeignKey('ad_accounts.id'), nullable=True),
        sa.Column('date_start', sa.String(), nullable=True),
        sa.Column('date_stop', sa.String(), nullable=True),
        sa.Column('spend', sa.Float(), server_default='0.0'),
        sa.Column('revenue', sa.Float(), server_default='0.0'),
        sa.Column('purchases', sa.Integer(), server_default='0'),
        sa.Column('impressions', sa.Integer(), server_default='0'),
        sa.Column('reach', sa.Integer(), server_default='0'),
        sa.Column('clicks', sa.Integer(), server_default='0'),
        sa.Column('ctr', sa.Float(), server_default='0.0'),
        sa.Column('cpc', sa.Float(), server_default='0.0'),
        sa.Column('cpm', sa.Float(), server_default='0.0'),
        sa.Column('cpa', sa.Float(), server_default='0.0'),
        sa.Column('frequency', sa.Float(), server_default='1.0'),
        sa.Column('roas', sa.Float(), server_default='0.0'),
        sa.Column('conversions', sa.Integer(), server_default='0'),
        sa.Column('cost_per_result', sa.Float(), server_default='0.0'),
        sa.Column('budget', sa.Float(), server_default='0.0'),
        sa.Column('status', sa.String(), server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'pixels',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('pixel_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('ad_account_id', sa.String(), sa.ForeignKey('ad_accounts.id'), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('health_score', sa.String(), server_default='optimal'),
        sa.Column('last_event_time', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('pixel_id')
    )

    op.create_table(
        'sync_jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('job_id', sa.String(), nullable=False),
        sa.Column('ad_account_id', sa.String(), nullable=True),
        sa.Column('sync_type', sa.String(), server_default='manual'),
        sa.Column('status', sa.String(), server_default='in_progress'),
        sa.Column('current_object', sa.String(), server_default='campaigns'),
        sa.Column('records_downloaded', sa.Integer(), server_default='0'),
        sa.Column('total_records', sa.Integer(), server_default='0'),
        sa.Column('progress_pct', sa.Float(), server_default='0.0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id')
    )

    op.create_table(
        'sync_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('sync_job_id', sa.String(), sa.ForeignKey('sync_jobs.id'), nullable=True),
        sa.Column('log_level', sa.String(), server_default='INFO'),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('object_type', sa.String(), nullable=True),
        sa.Column('records_count', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), server_default='usr_admin'),
        sa.Column('campaign_id', sa.String(), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('result', sa.String(), server_default='SUCCESS'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'reports',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('report_type', sa.String(), nullable=False),
        sa.Column('generated_by', sa.String(), server_default='usr_admin'),
        sa.Column('date_range', sa.String(), server_default='last_30_days'),
        sa.Column('filters', sa.Text(), nullable=True),
        sa.Column('export_format', sa.String(), server_default='PDF'),
        sa.Column('status', sa.String(), server_default='completed'),
        sa.Column('file_location', sa.String(), nullable=True),
        sa.Column('schedule', sa.String(), server_default='one_time'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'report_exports',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('report_id', sa.String(), sa.ForeignKey('reports.id'), nullable=False),
        sa.Column('export_format', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=True),
        sa.Column('file_size', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'report_history',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('report_id', sa.String(), sa.ForeignKey('reports.id'), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('status', sa.String(), server_default='completed'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'roles',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False, unique=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'permissions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False, unique=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'role_permissions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('role_id', sa.String(), sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('permission_id', sa.String(), sa.ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'user_roles',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role_id', sa.String(), sa.ForeignKey('roles.id', ondelete='CASCADE'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'sessions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('refresh_token', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'automation_rules',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('trigger_type', sa.String(), server_default='Campaign Spend', nullable=False),
        sa.Column('is_enabled', sa.Boolean(), server_default='true'),
        sa.Column('created_by', sa.String(), server_default='usr_admin'),
        sa.Column('schedule', sa.String(), server_default='Daily'),
        sa.Column('last_executed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('execution_count', sa.Integer(), server_default='0'),
        sa.Column('success_count', sa.Integer(), server_default='0'),
        sa.Column('failure_count', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'automation_conditions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('rule_id', sa.String(), sa.ForeignKey('automation_rules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('metric', sa.String(), nullable=False),
        sa.Column('operator', sa.String(), nullable=False),
        sa.Column('value', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'automation_actions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('rule_id', sa.String(), sa.ForeignKey('automation_rules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action_type', sa.String(), nullable=False),
        sa.Column('action_params', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'automation_executions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('rule_id', sa.String(), sa.ForeignKey('automation_rules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(), server_default='completed'),
        sa.Column('triggered_by', sa.String(), server_default='scheduler'),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'automation_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('execution_id', sa.String(), sa.ForeignKey('automation_executions.id', ondelete='CASCADE'), nullable=True),
        sa.Column('rule_id', sa.String(), sa.ForeignKey('automation_rules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('level', sa.String(), server_default='INFO'),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('automation_logs')
    op.drop_table('automation_executions')
    op.drop_table('automation_actions')
    op.drop_table('automation_conditions')
    op.drop_table('automation_rules')
    op.drop_table('sessions')
    op.drop_table('user_roles')
    op.drop_table('role_permissions')
    op.drop_table('permissions')
    op.drop_table('roles')
    op.drop_table('report_history')
    op.drop_table('report_exports')
    op.drop_table('reports')
    op.drop_table('audit_logs')
    op.drop_table('sync_logs')
    op.drop_table('sync_jobs')
    op.drop_table('pixels')
    op.drop_table('insights')
    op.drop_table('creatives')
    op.drop_table('ads')
    op.drop_table('ad_sets')
    op.drop_table('campaigns')
    op.drop_table('ad_accounts')
    op.drop_table('business_managers')
    op.drop_table('oauth_tokens')
    op.drop_table('meta_accounts')
    op.drop_table('users')
