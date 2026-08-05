export type MetaPlatformType = 'facebook' | 'instagram' | 'meta_bm' | 'meta_api' | 'meta_pixel' | 'meta_capi';

export interface MetaBusinessManager {
  id: string;
  name: string;
  verificationStatus: 'verified' | 'pending';
  adAccountsCount: number;
  isPrimary?: boolean;
}

export interface MetaAdAccount {
  id: string;
  accountName: string;
  accountId: string; // e.g. act_89201948201
  businessManagerId: string;
  businessManagerName: string;
  currency: string;
  timezone: string;
  spendLimit: number;
  amountSpent: number;
  status: 'active' | 'disabled' | 'pending_review';
  isPrimary?: boolean;
  pixelId?: string;
  pixelHealth?: 'optimal' | 'warning' | 'degraded';
  capiHealth?: 'optimal' | 'warning' | 'degraded';
}

export interface MetaTokenInfo {
  tokenType: 'long_lived_user' | 'system_user';
  accessTokenMasked: string;
  scopes: string[];
  expiresAt: string;
  isValid: boolean;
  lastRefreshed: string;
}

export interface MetricSummary {
  spend: number;
  spendChange: number;
  revenue: number;
  revenueChange: number;
  roas: number;
  roasChange: number;
  ctr: number;
  ctrChange: number;
  cpm: number;
  cpc: number;
  cpa: number;
  cpaChange: number;
  reach: number;
  impressions: number;
  frequency: number;
  clicks: number;
  purchases: number;
  leads: number;
  costPerResult: number;
  budget: number;
  campaignStatus: 'active' | 'paused' | 'learning';
  learningPhaseStatus: 'passed' | 'learning' | 'limited';
  adFatigueScore: number; // 0-100
  audienceSaturation: number; // 0-100
  pixelHealth: 'optimal' | 'warning' | 'degraded';
  conversionApiHealth: 'optimal' | 'warning' | 'degraded';
}

export interface Campaign {
  id: string;
  name: string;
  platform: 'facebook' | 'instagram' | 'meta_advantage_plus';
  status: 'active' | 'paused' | 'learning' | 'warning' | 'ended';
  dailyBudget: number;
  spend: number;
  revenue: number;
  roas: number;
  cpa: number;
  ctr: number;
  cpm: number;
  cpc: number;
  reach: number;
  impressions: number;
  frequency: number;
  clicks: number;
  purchases: number;
  leads: number;
  costPerResult: number;
  fatigueScore: number; // 0-100
  targetRoas: number;
  bidStrategy: string;
  adSetsCount: number;
  adsCount: number;
  audienceName: string;
  objective: 'Sales' | 'Leads' | 'Engagement' | 'Traffic' | 'Awareness';
  placements: string[];
  schedule: {
    startDate: string;
    endDate?: string;
    dayparting?: string;
  };
  targeting: {
    ageRange: string;
    gender: string;
    locations: string[];
    interests: string[];
    customAudiences: string[];
  };
  isDraft?: boolean;
  createdAt: string;
}

export interface MetaAdSet {
  id: string;
  campaignId: string;
  campaignName: string;
  name: string;
  status: 'active' | 'paused' | 'learning' | 'limited';
  dailyBudget: number;
  spend: number;
  revenue: number;
  roas: number;
  cpa: number;
  ctr: number;
  cpm: number;
  cpc: number;
  reach: number;
  impressions: number;
  frequency: number;
  clicks: number;
  purchases: number;
  leads: number;
  costPerResult: number;
  optimizationGoal: 'Purchases' | 'Leads' | 'Link Clicks' | 'Landing Page Views';
  targetingSummary: string;
  placements: string[];
  fatigueScore: number;
  adsCount: number;
}

export interface MetaAd {
  id: string;
  adSetId: string;
  adSetName: string;
  campaignId: string;
  campaignName: string;
  name: string;
  status: 'active' | 'paused' | 'rejected' | 'in_review';
  primaryText: string;
  headline: string;
  cta: string;
  format: 'Image' | 'Video' | 'Carousel' | 'Reels';
  thumbnailUrl: string;
  placements: string[];
  spend: number;
  revenue: number;
  roas: number;
  cpa: number;
  ctr: number;
  cpm: number;
  cpc: number;
  reach: number;
  impressions: number;
  clicks: number;
  purchases: number;
  leads: number;
  fatigueScore: number;
  textCoverage: number; // %
  hookRate: number; // %
}

export interface Agent {
  id: string;
  number: number;
  name: string;
  role: string;
  description: string;
  status: 'idle' | 'running' | 'completed' | 'alert';
  lastRun: string;
  impactScore: number;
  icon: string;
  insights: string[];
  recommendedActions: {
    title: string;
    description: string;
    type: 'budget' | 'pause' | 'audience' | 'creative' | 'rule';
    campaignId?: string;
    impact: string;
  }[];
}

export interface CopilotMessage {
  id: string;
  sender: 'user' | 'assistant' | 'system';
  text: string;
  timestamp: string;
  suggestedActions?: {
    id: string;
    label: string;
    type: 'pause' | 'budget' | 'creative' | 'duplicate' | 'report';
    payload?: any;
    executed?: boolean;
    requiresConfirmation?: boolean;
  }[];
  confirmationRequest?: {
    actionId: string;
    actionName: string;
    details: string;
    campaignName?: string;
    suggestedChange?: string;
    payload?: any;
  };
}

export interface CreativeAsset {
  id: string;
  title: string;
  platform: 'facebook' | 'instagram' | 'meta_reels';
  type: 'image' | 'video' | 'copy';
  thumbnail: string;
  ctr: number;
  roas: number;
  spend: number;
  conversions: number;
  fatigueScore: number;
  aiScore: number; // 0-100
  hookScore?: number;
  ctaScore?: number;
  contrastScore?: number;
  textRatio?: number;
  tags: string[];
}

export interface AudienceCluster {
  id: string;
  name: string;
  size: number;
  roasIndex: number;
  conversionRate: number;
  overlapPercentage: number;
  lookalikePercentage: number;
  interests: string[];
  suggestedKeywords: string[];
}

export interface AutomationRule {
  id: string;
  name: string;
  metric: 'roas' | 'cpa' | 'spend' | 'frequency' | 'ctr';
  operator: '>' | '<' | '>=';
  value: number;
  action: 'increase_budget' | 'decrease_budget' | 'pause_campaign' | 'send_alert';
  actionParameter?: string;
  isActive: boolean;
  lastTriggered?: string;
  triggerCount: number;
}

export interface SaaSUser {
  id?: string;
  name?: string;
  fullName?: string;
  email: string;
  avatar?: string;
  avatarUrl?: string;
  role: 'Owner' | 'Admin' | 'Marketer' | 'Viewer' | 'admin' | string;
  plan: 'Free' | 'Pro' | 'Agency' | 'Enterprise' | 'Enterprise Scale' | 'Billing not configured' | string;
  organization?: string;
  companyName?: string;
  membersCount?: number;
  apiCallsLimit?: number;
  apiCallsUsed?: number;
}
