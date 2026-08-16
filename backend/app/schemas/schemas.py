from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import List, Optional, Any, Dict, Union

class HealthResponse(BaseModel):
    status: str
    database: bool
    redis: bool
    version: str
    environment: str

class UserBase(BaseModel):
    email: str
    full_name: Optional[str] = None
    role: str = "Admin"
    company_name: Optional[str] = None
    plan: str = "Enterprise"

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: str
    is_active: bool
    is_verified: bool = True
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    company_name: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)

class VerifyEmailRequest(BaseModel):
    token: str

class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 1800
    user: Dict[str, Any]

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    company_name: Optional[str] = None
    is_active: Optional[bool] = None

class RoleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)

class PermissionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class UserRoleUpdateRequest(BaseModel):
    roles: List[str]


class MetaLoginResponse(BaseModel):
    authorization_url: str
    state: str

class MetaSelectionRequest(BaseModel):
    business_manager_id: str
    ad_account_id: str

class MetaAuthStatusResponse(BaseModel):
    connected: bool
    meta_user_id: Optional[str] = None
    meta_user_name: Optional[str] = None
    masked_token: Optional[str] = None
    token_type: Optional[str] = None
    is_valid: bool = False
    expires_at: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    last_connected: Optional[str] = None
    primary_business_name: Optional[str] = None
    primary_ad_account_name: Optional[str] = None

class BusinessManagerResponse(BaseModel):
    id: str
    bm_meta_id: str
    name: str
    verification_status: Optional[str] = None
    ad_accounts_count: int = 0
    is_primary: bool = False
    model_config = ConfigDict(from_attributes=True)

class AdAccountResponse(BaseModel):
    id: str
    account_id: str
    account_name: str
    business_manager_id: Optional[str] = None
    currency: Optional[str] = None
    timezone: Optional[str] = None
    spend_limit: Optional[float] = None
    amount_spent: float = 0.0
    status: Optional[str] = None
    pixel_id: Optional[str] = None
    pixel_health: Optional[str] = None
    capi_health: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class CampaignBase(BaseModel):
    name: str
    status: Optional[str] = None
    objective: Optional[str] = None
    buying_type: Optional[str] = None
    daily_budget: float = 0.0
    lifetime_budget: float = 0.0

class CampaignCreate(CampaignBase):
    campaign_id: str

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    daily_budget: Optional[float] = None
    lifetime_budget: Optional[float] = None

class CampaignRenameRequest(BaseModel):
    name: str

class CampaignBudgetActionRequest(BaseModel):
    percentage: Optional[float] = None
    amount: Optional[float] = None
    daily_budget: Optional[float] = None

class BulkCampaignActionRequest(BaseModel):
    campaign_ids: List[str]
    action: str  # pause, resume, update_budget, increase_budget, decrease_budget, delete, archive
    daily_budget: Optional[float] = None
    percentage: Optional[float] = None
    amount: Optional[float] = None

class CampaignAuditLogResponse(BaseModel):
    id: str
    user_id: str
    campaign_id: Optional[str] = None
    action: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    result: str = "SUCCESS"
    created_at: Any
    model_config = ConfigDict(from_attributes=True)

class CampaignResponse(CampaignBase):
    id: str
    campaign_id: str
    spend: float = 0.0
    revenue: float = 0.0
    roas: float = 0.0
    ctr: float = 0.0
    cpm: float = 0.0
    cpc: float = 0.0
    cpa: float = 0.0
    purchases: int = 0
    clicks: int = 0
    impressions: int = 0
    reach: int = 0
    learning_phase: str = "learning"
    model_config = ConfigDict(from_attributes=True)

class AdSetResponse(BaseModel):
    id: str
    ad_set_id: str
    name: str
    status: Optional[str] = None
    daily_budget: float = 0.0
    bid_strategy: Optional[str] = None
    optimization_goal: Optional[str] = None
    target_audience: Optional[str] = None
    cpa: float = 0.0
    roas: float = 0.0
    spend: float = 0.0
    model_config = ConfigDict(from_attributes=True)

class AdResponse(BaseModel):
    id: str
    ad_id: str
    name: str
    status: Optional[str] = None
    format: Optional[str] = None
    creative_title: Optional[str] = None
    creative_body: Optional[str] = None
    media_url: Optional[str] = None
    ctr: float = 0.0
    cpc: float = 0.0
    spend: float = 0.0
    fatigue_level: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class CreativeResponse(BaseModel):
    id: str
    creative_id: str
    name: str
    title: Optional[str] = None
    body: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    call_to_action: str = "LEARN_MORE"
    object_type: str = "SHARE"
    model_config = ConfigDict(from_attributes=True)

class PixelResponse(BaseModel):
    id: str
    pixel_id: str
    name: str
    is_active: bool = True
    health_score: str = "optimal"
    model_config = ConfigDict(from_attributes=True)

class CustomConversionResponse(BaseModel):
    id: str
    conversion_id: str
    name: str
    custom_event_type: str = "PURCHASE"
    rule: Optional[str] = None
    default_conversion_value: float = 0.0
    model_config = ConfigDict(from_attributes=True)

class CustomAudienceResponse(BaseModel):
    id: str
    audience_id: str
    name: str
    subtype: str = "CUSTOM"
    approximate_count: int = 0
    data_source: str = "Website Traffic"
    model_config = ConfigDict(from_attributes=True)

class MetricSummaryResponse(BaseModel):
    spend: float = 0.0
    revenue: float = 0.0
    roas: float = 0.0
    ctr: float = 0.0
    cpm: float = 0.0
    cpc: float = 0.0
    cpa: float = 0.0
    purchases: int = 0
    clicks: int = 0
    impressions: int = 0
    reach: int = 0
    budget: float = 0.0
    pixel_health: str = "optimal"
    conversion_api_health: str = "optimal"

class CopilotRequest(BaseModel):
    prompt: str
    context: Optional[dict] = None

class CopilotResponse(BaseModel):
    response: str
    recommendations: List[str] = Field(default_factory=list)
    actions: List[dict] = Field(default_factory=list)
    execution_plan: Optional[dict] = None
    observability: Optional[dict] = None

class CopilotExecutePlanRequest(BaseModel):
    plan: dict

class CopilotContextUpdateRequest(BaseModel):
    preferences: Optional[dict] = None
    pinned_campaign_id: Optional[str] = None
    pinned_campaign_name: Optional[str] = None

class CopilotSummaryRequest(BaseModel):
    summary_type: str = "daily"  # daily, weekly, monthly, executive
    period: Optional[str] = None

class CopilotSummaryResponse(BaseModel):
    summary_type: str
    title: str
    date_range: str
    total_spend: float
    total_revenue: float
    overall_roas: float
    average_cpa: float
    top_performing_campaign: Optional[str] = None
    worst_performing_campaign: Optional[str] = None
    key_insights: List[str] = Field(default_factory=list)
    actionable_recommendations: List[str] = Field(default_factory=list)
    generated_at: str

class WebSocketMessage(BaseModel):
    event: str
    data: Any

class SyncTriggerRequest(BaseModel):
    ad_account_id: Optional[str] = None
    sync_type: str = "manual"  # initial, incremental, manual, scheduled

class SyncStatusResponse(BaseModel):
    job_id: str
    ad_account_id: Optional[str] = None
    sync_type: str = "manual"
    status: str = "in_progress"
    current_object: str = "campaigns"
    records_downloaded: int = 0
    total_records: int = 0
    progress_pct: float = 0.0
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class InsightResponse(BaseModel):
    id: str
    campaign_id: Optional[str] = None
    ad_set_id: Optional[str] = None
    ad_id: Optional[str] = None
    ad_account_id: Optional[str] = None
    date_start: Optional[str] = None
    date_stop: Optional[str] = None
    spend: float = 0.0
    revenue: float = 0.0
    purchases: int = 0
    impressions: int = 0
    reach: int = 0
    clicks: int = 0
    ctr: float = 0.0
    cpc: float = 0.0
    cpm: float = 0.0
    cpa: float = 0.0
    frequency: float = 0.0
    roas: float = 0.0
    conversions: int = 0
    cost_per_result: float = 0.0
    budget: float = 0.0
    status: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class DashboardKPIsResponse(BaseModel):
    spend: float = 0.0
    revenue: float = 0.0
    roas: float = 0.0
    ctr: float = 0.0
    cpm: float = 0.0
    cpc: float = 0.0
    cpa: float = 0.0
    reach: int = 0
    impressions: int = 0
    frequency: float = 0.0
    purchases: int = 0
    conversions: int = 0
    budget: float = 0.0
    campaign_count: int = 0
    ad_set_count: int = 0
    ads_count: int = 0
    has_data: bool = False

class DashboardOverviewResponse(BaseModel):
    kpis: DashboardKPIsResponse
    last_sync_time: Optional[str] = None
    connection_status: str = "not_connected"
    is_synced: bool = False

class ChartDataPoint(BaseModel):
    date: str
    spend: float = 0.0
    revenue: float = 0.0
    roas: float = 0.0
    ctr: float = 0.0
    cpa: float = 0.0
    conversions: int = 0

class DashboardChartsResponse(BaseModel):
    spend_trend: List[ChartDataPoint] = Field(default_factory=list)
    revenue_trend: List[ChartDataPoint] = Field(default_factory=list)
    roas_trend: List[ChartDataPoint] = Field(default_factory=list)
    conversion_trend: List[ChartDataPoint] = Field(default_factory=list)

class TopCampaignItem(BaseModel):
    id: str
    name: str
    status: str
    spend: float
    revenue: float
    roas: float
    ctr: float
    cpa: float
    purchases: int

class TopAdItem(BaseModel):
    id: str
    name: str
    format: str
    status: str
    spend: float
    ctr: float
    cpc: float
    fatigue_level: Optional[str] = None

class BreakdownItem(BaseModel):
    dimension: str
    label: str
    spend: float = 0.0
    revenue: float = 0.0
    roas: float = 0.0
    purchases: int = 0
    impressions: int = 0
    clicks: int = 0
    ctr: float = 0.0
    cpa: float = 0.0
    percentage: float = 0.0

class CampaignComparisonItem(BaseModel):
    id: str
    name: str
    status: str
    objective: str
    spend: float
    revenue: float
    roas: float
    cpa: float
    ctr: float
    cpm: float
    cpc: float
    purchases: int
    impressions: int
    clicks: int
    roas_delta_pct: float = 0.0
    cpa_delta_pct: float = 0.0

class TimePerformanceItem(BaseModel):
    period: str
    spend: float = 0.0
    revenue: float = 0.0
    roas: float = 0.0
    purchases: int = 0
    clicks: int = 0
    impressions: int = 0
    ctr: float = 0.0
    cpa: float = 0.0

class ComparisonSummaryResponse(BaseModel):
    current_period: DashboardKPIsResponse
    previous_period: DashboardKPIsResponse
    spend_growth_pct: float = 0.0
    revenue_growth_pct: float = 0.0
    roas_growth_pct: float = 0.0
    cpa_growth_pct: float = 0.0
    purchases_growth_pct: float = 0.0
    best_performer: Optional[TopCampaignItem] = None
    worst_performer: Optional[TopCampaignItem] = None

class ReportGenerateRequest(BaseModel):
    name: str
    report_type: str  # Executive Summary, Campaign Performance, Ad Set Performance, Ads Performance, Creative Performance, ROAS Report, CPA Report, CTR Report, Budget Utilization, Conversion Report, Daily Report, Weekly Report, Monthly Report, Custom Date Range
    date_range: str = "last_30_days"
    export_format: str = "PDF"  # PDF, Excel, CSV
    schedule: str = "one_time"  # one_time, daily, weekly, monthly
    filters: Optional[dict] = None

class ReportResponse(BaseModel):
    id: str
    name: str
    report_type: str
    generated_by: str
    date_range: str
    filters: Optional[str] = None
    export_format: str
    status: str
    file_location: Optional[str] = None
    schedule: str = "one_time"
    created_at: Any
    model_config = ConfigDict(from_attributes=True)

    fatigue_level: str

class TrendItem(BaseModel):
    metric: str
    current_value: float
    previous_value: float = 0.0
    percent_change: Optional[float] = None
    direction: str = "flat"

class ConditionBase(BaseModel):
    metric: str
    operator: str
    value: str

class ActionBase(BaseModel):
    action_type: str
    action_params: Optional[str] = None

class AutomationRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    trigger_type: str = "Campaign Spend"
    schedule: str = "Daily"
    conditions: List[ConditionBase] = Field(default_factory=list)
    actions: List[ActionBase] = Field(default_factory=list)

class AutomationRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_type: Optional[str] = None
    schedule: Optional[str] = None
    is_enabled: Optional[bool] = None

class AutomationRuleResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    trigger_type: str
    is_enabled: bool
    created_by: str
    schedule: str
    last_executed: Optional[Any] = None
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    conditions: List[ConditionBase] = Field(default_factory=list)
    actions: List[ActionBase] = Field(default_factory=list)
    created_at: Any
    model_config = ConfigDict(from_attributes=True)

class AutomationExecutionResponse(BaseModel):
    id: str
    rule_id: str
    status: str
    triggered_by: str
    details: Optional[str] = None
    created_at: Any
    model_config = ConfigDict(from_attributes=True)

class AutomationLogResponse(BaseModel):
    id: str
    execution_id: Optional[str] = None
    rule_id: str
    level: str
    message: str
    created_at: Any
    model_config = ConfigDict(from_attributes=True)

# =============================================================================
# Enterprise Multi-Tenant SaaS Schemas
# =============================================================================

class OrganizationCreate(BaseModel):
    name: str
    domain: Optional[str] = None

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    is_active: Optional[bool] = None

class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    domain: Optional[str] = None
    is_active: bool
    created_at: Any

class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    workspace_type: Optional[str] = "Marketing Team"

class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    workspace_type: Optional[str] = None

class WorkspaceResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: Optional[str] = None
    workspace_type: str
    created_at: Any

class InvitationCreate(BaseModel):
    email: str
    role: Optional[str] = "Manager"
    workspace_id: Optional[str] = None

class InvitationAcceptRequest(BaseModel):
    token: str

class SubscriptionUpdate(BaseModel):
    plan_id: str

# =============================================================================
# Enterprise Billing & Subscription Schemas
# =============================================================================

class SubscribeRequest(BaseModel):
    plan_id: str
    provider: Optional[str] = "stripe"
    payment_method_id: Optional[str] = None

class ChangePlanRequest(BaseModel):
    new_plan_id: str

class PaymentWebhookRequest(BaseModel):
    event: Optional[str] = None
    type: Optional[str] = None
    organization_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

class RefundRequest(BaseModel):
    payment_id: str
    amount: float
    reason: Optional[str] = "Customer requested refund"

# =============================================================================
# White Label, Custom Domains & Agency Platform Schemas
# =============================================================================

class BrandingConfigResponse(BaseModel):
    organization_id: str
    brand_name: str
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    primary_color: str
    secondary_color: str
    accent_color: str
    font_family: str
    login_bg_url: Optional[str] = None
    dashboard_title: str
    dashboard_banner_url: Optional[str] = None
    email_header_logo: Optional[str] = None
    email_footer_text: str
    email_from_name: str
    email_from_address: str
    pdf_header_logo: Optional[str] = None
    pdf_footer_text: str
    pdf_primary_color: str
    invoice_company_name: str
    invoice_company_address: str
    invoice_logo_url: Optional[str] = None
    loader_icon_url: Optional[str] = None
    loader_text: str
    custom_css: Optional[str] = None

class BrandingConfigUpdate(BaseModel):
    brand_name: Optional[str] = None
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    font_family: Optional[str] = None
    login_bg_url: Optional[str] = None
    dashboard_title: Optional[str] = None
    dashboard_banner_url: Optional[str] = None
    email_header_logo: Optional[str] = None
    email_footer_text: Optional[str] = None
    email_from_name: Optional[str] = None
    email_from_address: Optional[str] = None
    pdf_header_logo: Optional[str] = None
    pdf_footer_text: Optional[str] = None
    pdf_primary_color: Optional[str] = None
    invoice_company_name: Optional[str] = None
    invoice_company_address: Optional[str] = None
    invoice_logo_url: Optional[str] = None
    loader_icon_url: Optional[str] = None
    loader_text: Optional[str] = None
    custom_css: Optional[str] = None

class CustomDomainCreate(BaseModel):
    domain: str

class CustomDomainResponse(BaseModel):
    id: str
    organization_id: str
    domain: str
    cname_target: str
    txt_record_name: str
    txt_record_value: str
    status: str
    ssl_status: str
    verified_at: Optional[Any] = None
    created_at: Any

class AgencyClientCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    domain: Optional[str] = None
    parent_agency_id: Optional[str] = None
    admin_email: Optional[str] = None

class AgencyClientResponse(BaseModel):
    id: str
    name: str
    slug: str
    domain: Optional[str] = None
    parent_agency_id: Optional[str] = None
    is_active: bool
    created_at: Any

class AgencySwitchRequest(BaseModel):
    target_client_id: str

class AgencySwitchResponse(BaseModel):
    status: str
    active_organization_id: str
    active_organization_name: str
    brand_name: str
    message: str

class EmailTemplateUpdate(BaseModel):
    template_type: str
    subject: str
    body_html: str
    is_active: Optional[bool] = True

class EmailTemplateResponse(BaseModel):
    id: str
    organization_id: str
    template_type: str
    subject: str
    body_html: str
    is_active: bool
    updated_at: Any

class AuditLogResponse(BaseModel):
    id: str
    organization_id: str
    user_id: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    created_at: Any

# =============================================================================
# Enterprise Security Hardening & Compliance Schemas
# =============================================================================

class SecurityStatusResponse(BaseModel):
    mfa_enabled: bool
    passkeys_count: int
    active_sessions_count: int
    trusted_devices_count: int
    ip_rules_count: int
    active_alerts_count: int
    recovery_codes_left: int
    last_password_change: Optional[Any] = None
    security_score: int

class MFASetupResponse(BaseModel):
    secret: str
    qr_uri: str
    recovery_codes: List[str]
    message: str

class MFAVerifyRequest(BaseModel):
    code: str

class MFAVerifyResponse(BaseModel):
    status: str
    mfa_enabled: bool
    message: str

class PasskeyRegisterRequest(BaseModel):
    name: Optional[str] = "Hardware Security Key"
    credential_id: Optional[str] = None
    public_key: Optional[str] = None
    transports: Optional[List[str]] = None
    device_type: Optional[str] = "platform"

class PasskeyVerifyRequest(BaseModel):
    credential_id: str
    signature: Optional[str] = None
    client_data_json: Optional[str] = None

class SessionResponse(BaseModel):
    id: str
    user_id: str
    organization_id: str
    device_name: str
    device_type: str
    browser: str
    ip_address: str
    country: str
    is_trusted: bool
    is_current: bool
    last_activity: Any
    expires_at: Any
    is_revoked: bool

class IPSecurityRuleCreate(BaseModel):
    rule_type: str  # allow, block
    ip_or_cidr: str
    country_code: Optional[str] = None
    reason: Optional[str] = "Enterprise Policy"

class IPSecurityRuleResponse(BaseModel):
    id: str
    organization_id: str
    rule_type: str
    ip_or_cidr: str
    country_code: Optional[str] = None
    reason: str
    is_active: bool
    created_at: Any

class SecurityAlertResponse(BaseModel):
    id: str
    organization_id: str
    user_id: str
    alert_type: str
    severity: str
    title: str
    description: str
    ip_address: Optional[str] = None
    location: Optional[str] = None
    status: str
    created_at: Any

class WebhookEventResponse(BaseModel):
    id: str
    event_id: str
    object_type: str
    entry_id: Optional[str] = None
    field_name: Optional[str] = None
    payload: Any
    status: str
    retry_count: int
    error_message: Optional[str] = None
    signature_verified: bool
    received_at: Any
    processed_at: Any = None
    model_config = ConfigDict(from_attributes=True)

class WebhookReprocessResponse(BaseModel):
    event_id: str
    status: str
    message: str

class LeadEventResponse(BaseModel):
    id: str
    leadgen_id: str
    form_id: Optional[str] = None
    ad_id: Optional[str] = None
    adgroup_id: Optional[str] = None
    campaign_id: Optional[str] = None
    page_id: Optional[str] = None
    lead_data: Any = None
    created_time: Any
    model_config = ConfigDict(from_attributes=True)

class MessengerEventResponse(BaseModel):
    id: str
    mid: str
    sender_id: str
    recipient_id: str
    message_text: Optional[str] = None
    attachments: Any = None
    timestamp: Any
    model_config = ConfigDict(from_attributes=True)

class MetaCapiUserData(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    client_ip_address: Optional[str] = None
    client_user_agent: Optional[str] = None
    fbc: Optional[str] = None
    fbp: Optional[str] = None

class MetaCapiCustomData(BaseModel):
    currency: Optional[str] = None
    value: Optional[float] = None
    content_name: Optional[str] = None
    content_ids: Optional[List[str]] = None
    num_items: Optional[int] = None

class MetaCapiEventRequest(BaseModel):
    pixel_id: str
    event_name: str
    event_time: Optional[int] = None
    action_source: str
    event_source_url: Optional[str] = None
    user_data: Optional[MetaCapiUserData] = None
    custom_data: Optional[MetaCapiCustomData] = None
    test_event_code: Optional[str] = None

class MetaCapiEventResponse(BaseModel):
    status: str
    events_received: int
    messages: List[str] = Field(default_factory=list)
    fbtrace_id: Optional[str] = None
    event_name: str
    pixel_id: str

class MetaPermissionItem(BaseModel):
    permission: str
    status: str  # granted, declined

class MetaPermissionsResponse(BaseModel):
    is_valid: bool = True
    meta_user_id: str
    permissions: List[MetaPermissionItem] = Field(default_factory=list)
    granted_scopes: List[str] = Field(default_factory=list)
    declined_scopes: List[str] = Field(default_factory=list)






