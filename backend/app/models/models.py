from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, JSON, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, default="Admin")
    company_name = Column(String, nullable=True)
    plan = Column(String, default="Enterprise")
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=True)
    verification_token = Column(String, nullable=True)
    reset_token = Column(String, nullable=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class MetaAccount(Base):
    __tablename__ = "meta_accounts"

    id = Column(String, primary_key=True, default=generate_uuid)
    meta_user_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    connection_status = Column(String, default="connected")
    last_connected = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    tokens = relationship("OAuthToken", back_populates="meta_account", cascade="all, delete-orphan")
    business_managers = relationship("BusinessManager", back_populates="meta_account")
    ad_accounts = relationship("AdAccount", back_populates="meta_account")

class OAuthToken(Base):
    __tablename__ = "oauth_tokens"

    id = Column(String, primary_key=True, default=generate_uuid)
    meta_account_id = Column(String, ForeignKey("meta_accounts.id"), nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    encrypted_access_token = Column(Text, nullable=False)
    token_type = Column(String, default="long_lived_user")
    scopes = Column(JSON, default=list)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_refreshed = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_valid = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    meta_account = relationship("MetaAccount", back_populates="tokens")

class BusinessManager(Base):
    __tablename__ = "business_managers"

    id = Column(String, primary_key=True, default=generate_uuid)
    bm_meta_id = Column(String, unique=True, index=True, nullable=False)
    meta_account_id = Column(String, ForeignKey("meta_accounts.id"), nullable=True)
    name = Column(String, nullable=False)
    verification_status = Column(String, default="verified")
    ad_accounts_count = Column(Integer, default=1)
    is_primary = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    meta_account = relationship("MetaAccount", back_populates="business_managers")
    ad_accounts = relationship("AdAccount", back_populates="business_manager")

class AdAccount(Base):
    __tablename__ = "ad_accounts"

    id = Column(String, primary_key=True, default=generate_uuid)
    account_name = Column(String, nullable=False)
    account_id = Column(String, unique=True, index=True, nullable=False)
    meta_account_id = Column(String, ForeignKey("meta_accounts.id"), nullable=True)
    business_manager_id = Column(String, ForeignKey("business_managers.id"), nullable=True)
    currency = Column(String, default="USD")
    timezone = Column(String, default="America/New_York")
    spend_limit = Column(Float, default=250000.0)
    amount_spent = Column(Float, default=0.0)
    status = Column(String, default="active")
    pixel_id = Column(String, nullable=True)
    pixel_health = Column(String, default="optimal")
    capi_health = Column(String, default="optimal")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    meta_account = relationship("MetaAccount", back_populates="ad_accounts")
    business_manager = relationship("BusinessManager", back_populates="ad_accounts")

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String, primary_key=True, default=generate_uuid)
    campaign_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    ad_account_id = Column(String, ForeignKey("ad_accounts.id"), nullable=True, index=True)
    status = Column(String, default="ACTIVE", index=True)
    objective = Column(String, default="OUTCOME_SALES", index=True)
    buying_type = Column(String, default="AUCTION")
    daily_budget = Column(Float, default=0.0)
    lifetime_budget = Column(Float, default=0.0)
    spend = Column(Float, default=0.0)
    revenue = Column(Float, default=0.0)
    roas = Column(Float, default=0.0)
    ctr = Column(Float, default=0.0)
    cpm = Column(Float, default=0.0)
    cpc = Column(Float, default=0.0)
    cpa = Column(Float, default=0.0)
    purchases = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    reach = Column(Integer, default=0)
    learning_phase = Column(String, default="learning")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

class MetaAdSet(Base):
    __tablename__ = "ad_sets"

    id = Column(String, primary_key=True, default=generate_uuid)
    ad_set_id = Column(String, unique=True, index=True, nullable=False)
    campaign_id = Column(String, ForeignKey("campaigns.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    status = Column(String, default="ACTIVE", index=True)
    daily_budget = Column(Float, default=0.0)
    bid_strategy = Column(String, default="LOWEST_COST_WITHOUT_CAP")
    optimization_goal = Column(String, default="OFFSITE_CONVERSIONS")
    target_audience = Column(String, nullable=True)
    cpa = Column(Float, default=0.0)
    roas = Column(Float, default=0.0)
    spend = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

class MetaAd(Base):
    __tablename__ = "ads"

    id = Column(String, primary_key=True, default=generate_uuid)
    ad_id = Column(String, unique=True, index=True, nullable=False)
    ad_set_id = Column(String, ForeignKey("ad_sets.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    status = Column(String, default="ACTIVE", index=True)
    format = Column(String, default="Video")
    creative_title = Column(String, nullable=True)
    creative_body = Column(Text, nullable=True)
    media_url = Column(String, nullable=True)
    ctr = Column(Float, default=0.0)
    cpc = Column(Float, default=0.0)
    spend = Column(Float, default=0.0)
    fatigue_level = Column(String, default="Low")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

class Creative(Base):
    __tablename__ = "creatives"

    id = Column(String, primary_key=True, default=generate_uuid)
    creative_id = Column(String, unique=True, index=True, nullable=False)
    ad_account_id = Column(String, ForeignKey("ad_accounts.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    title = Column(String, nullable=True)
    body = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    video_url = Column(String, nullable=True)
    call_to_action = Column(String, default="LEARN_MORE")
    object_type = Column(String, default="SHARE")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

class Insight(Base):
    __tablename__ = "insights"

    id = Column(String, primary_key=True, default=generate_uuid)
    campaign_id = Column(String, ForeignKey("campaigns.id"), nullable=True, index=True)
    ad_set_id = Column(String, ForeignKey("ad_sets.id"), nullable=True, index=True)
    ad_id = Column(String, ForeignKey("ads.id"), nullable=True, index=True)
    ad_account_id = Column(String, ForeignKey("ad_accounts.id"), nullable=True, index=True)
    date_start = Column(String, nullable=True, index=True)
    date_stop = Column(String, nullable=True, index=True)
    spend = Column(Float, default=0.0)
    revenue = Column(Float, default=0.0)
    purchases = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    reach = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    ctr = Column(Float, default=0.0)
    cpc = Column(Float, default=0.0)
    cpm = Column(Float, default=0.0)
    cpa = Column(Float, default=0.0)
    frequency = Column(Float, default=1.0)
    roas = Column(Float, default=0.0)
    conversions = Column(Integer, default=0)
    cost_per_result = Column(Float, default=0.0)
    budget = Column(Float, default=0.0)
    status = Column(String, default="ACTIVE", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        Index("idx_insights_campaign_date", "campaign_id", "date_start"),
        Index("idx_insights_account_date", "ad_account_id", "date_start"),
    )

class Pixel(Base):
    __tablename__ = "pixels"

    id = Column(String, primary_key=True, default=generate_uuid)
    pixel_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    ad_account_id = Column(String, ForeignKey("ad_accounts.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    health_score = Column(String, default="optimal")
    last_event_time = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class CustomConversion(Base):
    __tablename__ = "custom_conversions"

    id = Column(String, primary_key=True, default=generate_uuid)
    conversion_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    ad_account_id = Column(String, ForeignKey("ad_accounts.id"), nullable=True)
    custom_event_type = Column(String, default="PURCHASE")
    rule = Column(Text, nullable=True)
    default_conversion_value = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class CustomAudience(Base):
    __tablename__ = "custom_audiences"

    id = Column(String, primary_key=True, default=generate_uuid)
    audience_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    ad_account_id = Column(String, ForeignKey("ad_accounts.id"), nullable=True)
    subtype = Column(String, default="CUSTOM")  # CUSTOM, LOOKALIKE
    approximate_count = Column(Integer, default=0)
    data_source = Column(String, default="Website Traffic")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SyncJob(Base):
    __tablename__ = "sync_jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, unique=True, index=True, nullable=False)
    ad_account_id = Column(String, nullable=True)
    sync_type = Column(String, default="manual")  # initial, incremental, manual, scheduled
    status = Column(String, default="in_progress")  # pending, in_progress, completed, failed
    current_object = Column(String, default="campaigns")  # campaigns, adsets, ads, creatives, insights
    records_downloaded = Column(Integer, default=0)
    total_records = Column(Integer, default=0)
    progress_pct = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    sync_job_id = Column(String, ForeignKey("sync_jobs.id"), nullable=True)
    log_level = Column(String, default="INFO")
    message = Column(Text, nullable=False)
    object_type = Column(String, nullable=True)
    records_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, nullable=True, index=True)
    user_id = Column(String, default="usr_admin", index=True)
    campaign_id = Column(String, nullable=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, default="campaign")
    resource_id = Column(String, nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    result = Column(String, default="SUCCESS")
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    report_type = Column(String, nullable=False)
    generated_by = Column(String, default="usr_admin")
    date_range = Column(String, default="last_30_days")
    filters = Column(Text, nullable=True)
    export_format = Column(String, default="PDF")
    status = Column(String, default="completed")  # pending, processing, completed, failed
    file_location = Column(String, nullable=True)
    schedule = Column(String, default="one_time")  # one_time, daily, weekly, monthly
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ReportExport(Base):
    __tablename__ = "report_exports"

    id = Column(String, primary_key=True, default=generate_uuid)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False)
    export_format = Column(String, nullable=False)
    file_path = Column(String, nullable=True)
    file_size = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ReportHistory(Base):
    __tablename__ = "report_history"

    id = Column(String, primary_key=True, default=generate_uuid)
    report_id = Column(String, ForeignKey("reports.id"), nullable=False)
    action = Column(String, nullable=False)
    status = Column(String, default="completed")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Role(Base):
    __tablename__ = "roles"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)

class RolePermission(Base):
    __tablename__ = "role_permissions"

    id = Column(String, primary_key=True, default=generate_uuid)
    role_id = Column(String, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    permission_id = Column(String, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False)

class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(String, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)

class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AutomationRule(Base):
    __tablename__ = "automation_rules"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    metric = Column(String, nullable=True)
    operator = Column(String, nullable=True)
    value = Column(Float, nullable=True)
    action = Column(String, nullable=True)
    trigger_type = Column(String, nullable=False, default="Campaign Spend")
    is_enabled = Column(Boolean, default=True)
    enabled = Column(Boolean, default=True)
    created_by = Column(String, default="usr_admin")
    schedule = Column(String, default="Daily")  # Daily, Weekly, Monthly, Realtime
    last_executed = Column(DateTime(timezone=True), nullable=True)
    last_run = Column(String, default="Never")
    triggered_count = Column(Integer, default=0)
    execution_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AutomationCondition(Base):
    __tablename__ = "automation_conditions"

    id = Column(String, primary_key=True, default=generate_uuid)
    rule_id = Column(String, ForeignKey("automation_rules.id", ondelete="CASCADE"), nullable=False)
    metric = Column(String, nullable=False)  # ROAS, Campaign Spend, CPA, CTR, CPC, Conversions, Revenue, etc.
    operator = Column(String, nullable=False)  # >, <, >=, <=, ==, !=, Between
    value = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AutomationAction(Base):
    __tablename__ = "automation_actions"

    id = Column(String, primary_key=True, default=generate_uuid)
    rule_id = Column(String, ForeignKey("automation_rules.id", ondelete="CASCADE"), nullable=False)
    action_type = Column(String, nullable=False)  # Pause Campaign, Resume Campaign, Increase Budget, Decrease Budget, etc.
    action_params = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AutomationExecution(Base):
    __tablename__ = "automation_executions"

    id = Column(String, primary_key=True, default=generate_uuid)
    rule_id = Column(String, ForeignKey("automation_rules.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, default="completed")  # running, completed, failed
    triggered_by = Column(String, default="scheduler")
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AutomationLog(Base):
    __tablename__ = "automation_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    execution_id = Column(String, ForeignKey("automation_executions.id", ondelete="CASCADE"), nullable=True)
    rule_id = Column(String, ForeignKey("automation_rules.id", ondelete="CASCADE"), nullable=False)
    level = Column(String, default="INFO")
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# =============================================================================
# Enterprise Multi-Tenant Architecture Models
# =============================================================================

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, index=True)
    slug = Column(String, unique=True, index=True, nullable=False)
    domain = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, default="Member")  # Owner, Admin, Manager, Analyst, Viewer
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

class OrganizationSettings(Base):
    __tablename__ = "organization_settings"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    currency = Column(String, default="USD")
    timezone = Column(String, default="America/New_York")
    ai_opt_in = Column(Boolean, default=True)
    max_campaigns = Column(Integer, default=50)
    settings_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    workspace_type = Column(String, default="Marketing Team")  # Marketing Team, Sales Team, Clients, Agencies
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    id = Column(String, primary_key=True, default=generate_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String, default="Workspace Admin")  # Workspace Admin, Member, Viewer
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

class Invitation(Base):
    __tablename__ = "invitations"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True)
    email = Column(String, nullable=False, index=True)
    role = Column(String, default="Manager")
    token = Column(String, unique=True, nullable=False, index=True)
    status = Column(String, default="pending")  # pending, accepted, expired, revoked
    invited_by = Column(String, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, nullable=False)  # Free, Starter, Professional, Enterprise
    monthly_price = Column(Float, default=0.0)
    seats_included = Column(Integer, default=5)
    max_campaigns = Column(Integer, default=100)
    sync_frequency_minutes = Column(Integer, default=15)
    automation_limit = Column(Integer, default=20)
    ai_token_monthly_limit = Column(Integer, default=1000000)
    storage_gb = Column(Integer, default=10)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    plan_id = Column(String, ForeignKey("subscription_plans.id"), nullable=False)
    status = Column(String, default="active")  # active, canceled, past_due
    current_period_start = Column(DateTime(timezone=True), server_default=func.now())
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UsageMetric(Base):
    __tablename__ = "usage_metrics"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    metric_type = Column(String, nullable=False)  # api_requests, ai_tokens, report_generations, automation_executions, campaign_syncs, storage_bytes
    quantity = Column(Integer, default=1)
    period_start = Column(DateTime(timezone=True), server_default=func.now())
    period_end = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    key_hash = Column(String, unique=True, nullable=False, index=True)
    prefix = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# =============================================================================
# Enterprise Billing & Subscription Platform Models
# =============================================================================

class PaymentCustomer(Base):
    __tablename__ = "payment_customers"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String, nullable=False, default="stripe")  # stripe, razorpay
    provider_customer_id = Column(String, nullable=False, index=True)
    email = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PaymentMethodModel(Base):
    __tablename__ = "payment_methods"

    id = Column(String, primary_key=True, default=generate_uuid)
    customer_id = Column(String, ForeignKey("payment_customers.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String, nullable=False, default="stripe")
    provider_payment_method_id = Column(String, nullable=False)
    type = Column(String, default="card")  # card, upi, netbanking
    brand = Column(String, nullable=True)  # visa, mastercard
    last4 = Column(String, nullable=True)
    exp_month = Column(Integer, nullable=True)
    exp_year = Column(Integer, nullable=True)
    is_default = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SubscriptionHistory(Base):
    __tablename__ = "subscription_history"

    id = Column(String, primary_key=True, default=generate_uuid)
    subscription_id = Column(String, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(String, ForeignKey("subscription_plans.id"), nullable=False)
    event_type = Column(String, nullable=False)  # created, upgraded, downgraded, canceled, resumed, renewed
    previous_plan_id = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class InvoiceModel(Base):
    __tablename__ = "invoices"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_number = Column(String, unique=True, nullable=False, index=True)
    provider = Column(String, default="internal")  # stripe, razorpay, internal
    provider_invoice_id = Column(String, nullable=True)
    amount_due = Column(Float, default=0.0)
    amount_paid = Column(Float, default=0.0)
    currency = Column(String, default="USD")
    status = Column(String, default="paid")  # paid, open, void, uncollectible
    tax_amount = Column(Float, default=0.0)
    pdf_url = Column(String, nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(String, primary_key=True, default=generate_uuid)
    invoice_id = Column(String, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    description = Column(String, nullable=False)
    quantity = Column(Integer, default=1)
    unit_amount = Column(Float, default=0.0)
    amount = Column(Float, default=0.0)
    currency = Column(String, default="USD")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PaymentModel(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_id = Column(String, ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True)
    provider = Column(String, default="stripe")
    provider_payment_id = Column(String, nullable=False, index=True)
    amount = Column(Float, default=0.0)
    currency = Column(String, default="USD")
    status = Column(String, default="succeeded")  # succeeded, failed, pending, refunded
    idempotency_key = Column(String, unique=True, nullable=True, index=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class RefundModel(Base):
    __tablename__ = "refunds"

    id = Column(String, primary_key=True, default=generate_uuid)
    payment_id = Column(String, ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    provider_refund_id = Column(String, nullable=False)
    amount = Column(Float, default=0.0)
    currency = Column(String, default="USD")
    reason = Column(String, nullable=True)
    status = Column(String, default="succeeded")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class CouponCode(Base):
    __tablename__ = "coupon_codes"

    id = Column(String, primary_key=True, default=generate_uuid)
    code = Column(String, unique=True, nullable=False, index=True)
    discount_type = Column(String, default="percentage")  # percentage, fixed
    discount_value = Column(Float, default=10.0)
    max_redemptions = Column(Integer, default=100)
    times_redeemed = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DiscountModel(Base):
    __tablename__ = "discounts"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    coupon_id = Column(String, ForeignKey("coupon_codes.id", ondelete="CASCADE"), nullable=False)
    applied_at = Column(DateTime(timezone=True), server_default=func.now())

class BillingEvent(Base):
    __tablename__ = "billing_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, nullable=True, index=True)
    provider = Column(String, nullable=False)  # stripe, razorpay
    event_type = Column(String, nullable=False)
    event_data = Column(JSON, nullable=True)
    processed = Column(Boolean, default=True)
    error_log = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# =============================================================================
# White Label, Custom Domains & Agency Platform Models
# =============================================================================

class BrandingConfig(Base):
    __tablename__ = "branding_configs"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    brand_name = Column(String, default="MetaMind AI")
    logo_url = Column(String, nullable=True)
    favicon_url = Column(String, nullable=True)
    primary_color = Column(String, default="#4F46E5")
    secondary_color = Column(String, default="#06B6D4")
    accent_color = Column(String, default="#10B981")
    font_family = Column(String, default="Inter, sans-serif")
    login_bg_url = Column(String, nullable=True)
    dashboard_title = Column(String, default="MetaMind Analytics Dashboard")
    dashboard_banner_url = Column(String, nullable=True)
    email_header_logo = Column(String, nullable=True)
    email_footer_text = Column(String, default="Powered by MetaMind Enterprise Platform")
    email_from_name = Column(String, default="MetaMind Notifications")
    email_from_address = Column(String, default="notifications@metamind.ai")
    pdf_header_logo = Column(String, nullable=True)
    pdf_footer_text = Column(String, default="Confidential Executive Performance Report")
    pdf_primary_color = Column(String, default="#4F46E5")
    invoice_company_name = Column(String, default="MetaMind Technologies Inc.")
    invoice_company_address = Column(String, default="100 AI Boulevard, San Francisco, CA")
    invoice_logo_url = Column(String, nullable=True)
    loader_icon_url = Column(String, nullable=True)
    loader_text = Column(String, default="Loading MetaMind Platform...")
    custom_css = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class CustomDomain(Base):
    __tablename__ = "custom_domains"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    domain = Column(String, unique=True, nullable=False, index=True)
    cname_target = Column(String, default="cname.metamind.ai")
    txt_record_name = Column(String, nullable=False)
    txt_record_value = Column(String, nullable=False)
    status = Column(String, default="pending_verification")  # pending_verification, verified, failed
    ssl_status = Column(String, default="pending")  # pending, provisioned, active
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AgencyClientLink(Base):
    __tablename__ = "agency_client_links"

    id = Column(String, primary_key=True, default=generate_uuid)
    agency_organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    client_organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_agency_id = Column(String, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)  # agency hierarchy
    access_role = Column(String, default="Agency Admin")
    permissions_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ClientPortalSettings(Base):
    __tablename__ = "client_portal_settings"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    portal_title = Column(String, default="Client Analytics Portal")
    login_enabled = Column(Boolean, default=True)
    allow_exports = Column(Boolean, default=True)
    read_only_default = Column(Boolean, default=True)
    allowed_modules = Column(JSON, default=list)
    custom_welcome_msg = Column(Text, nullable=True)

class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    template_type = Column(String, nullable=False, index=True)  # invitation, password_reset, billing, report_ready, automation_alert, ai_notification
    subject = Column(String, nullable=False)
    body_html = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# =============================================================================
# Enterprise Security Hardening & Compliance Models
# =============================================================================

class UserSecurityConfig(Base):
    __tablename__ = "user_security_configs"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, unique=True, nullable=False, index=True)
    mfa_secret = Column(String, nullable=True)
    mfa_enabled = Column(Boolean, default=False)
    recovery_codes = Column(JSON, default=list)
    password_hash = Column(String, nullable=True)
    password_history = Column(JSON, default=list)
    last_password_change = Column(DateTime(timezone=True), nullable=True)
    session_timeout_minutes = Column(Integer, default=30)
    max_concurrent_sessions = Column(Integer, default=5)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class PasskeyCredential(Base):
    __tablename__ = "passkey_credentials"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, nullable=False, index=True)
    credential_id = Column(String, unique=True, nullable=False, index=True)
    public_key = Column(Text, nullable=False)
    name = Column(String, default="Hardware Security Key / Passkey")
    transports = Column(JSON, default=list)  # usb, nfc, ble, internal
    device_type = Column(String, default="platform")  # platform, cross-platform
    counter = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)

class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, nullable=False, index=True)
    organization_id = Column(String, nullable=False, index=True)
    session_token = Column(String, unique=True, nullable=False, index=True)
    device_name = Column(String, default="Chrome on macOS")
    device_type = Column(String, default="desktop")  # desktop, mobile, tablet
    browser = Column(String, default="Chrome 122.0")
    ip_address = Column(String, default="127.0.0.1")
    country = Column(String, default="United States")
    is_trusted = Column(Boolean, default=True)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False)

class IPSecurityRule(Base):
    __tablename__ = "ip_security_rules"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_type = Column(String, nullable=False)  # allow, block
    ip_or_cidr = Column(String, nullable=False)
    country_code = Column(String, nullable=True)
    reason = Column(String, default="Enterprise Security Policy")
    created_by = Column(String, default="usr_admin")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SecurityAlert(Base):
    __tablename__ = "security_alerts"

    id = Column(String, primary_key=True, default=generate_uuid)
    organization_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    alert_type = Column(String, nullable=False)  # failed_login, impossible_travel, rate_limit_violation, mfa_failure, suspicious_ip
    severity = Column(String, default="medium")  # low, medium, high, critical
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    ip_address = Column(String, nullable=True)
    location = Column(String, nullable=True)
    status = Column(String, default="active")  # active, resolved, dismissed
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# =============================================================================
# Meta Webhook Models
# =============================================================================

class MetaWebhookEvent(Base):
    __tablename__ = "meta_webhook_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    event_id = Column(String, unique=True, index=True, nullable=False)
    object_type = Column(String, nullable=False, index=True)  # campaign, adset, ad, creative, leadgen, messenger, page
    entry_id = Column(String, nullable=True, index=True)
    field_name = Column(String, nullable=True)
    payload = Column(JSON, nullable=False)
    status = Column(String, default="pending", index=True)  # pending, processed, failed
    retry_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    signature_verified = Column(Boolean, default=True)
    received_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

class LeadEvent(Base):
    __tablename__ = "lead_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    leadgen_id = Column(String, unique=True, index=True, nullable=False)
    form_id = Column(String, nullable=True, index=True)
    ad_id = Column(String, nullable=True, index=True)
    adgroup_id = Column(String, nullable=True)
    campaign_id = Column(String, nullable=True)
    page_id = Column(String, nullable=True)
    lead_data = Column(JSON, nullable=True)
    created_time = Column(DateTime(timezone=True), server_default=func.now())

class MessengerEvent(Base):
    __tablename__ = "messenger_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    mid = Column(String, unique=True, index=True, nullable=False)
    sender_id = Column(String, nullable=False, index=True)
    recipient_id = Column(String, nullable=False, index=True)
    message_text = Column(Text, nullable=True)
    attachments = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())








