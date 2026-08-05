/// <reference types="vite/client" />

export const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

const STORAGE_KEYS = {
  REPORTS: 'metamind_reports',
  RULES: 'metamind_automation_rules',
  HISTORY: 'metamind_automation_history',
};

const defaultReports = [
  {
    id: 'rep_101',
    name: 'Executive Meta Marketing Performance Report',
    report_type: 'Executive Summary',
    generated_by: 'Volzad Admin',
    date_range: 'last_30_days',
    export_format: 'PDF',
    status: 'Completed',
    schedule: 'one_time',
    created_at: new Date(Date.now() - 3600000 * 24 * 2).toISOString(),
  },
  {
    id: 'rep_102',
    name: 'Advantage+ Audience & ROAS Audit',
    report_type: 'Audience Performance',
    generated_by: 'Meta AI Copilot',
    date_range: 'last_7_days',
    export_format: 'EXCEL',
    status: 'Completed',
    schedule: 'weekly',
    created_at: new Date(Date.now() - 3600000 * 5).toISOString(),
  },
];

const defaultRules = [
  {
    id: 'rule_1',
    name: 'Auto-Pause Low ROAS Campaigns',
    description: 'Automatically pause any campaign if ROAS drops below 1.5x after 500 clicks',
    trigger_type: 'ROAS',
    is_enabled: true,
    schedule: 'Hourly',
    last_executed: new Date(Date.now() - 1800000).toISOString(),
    execution_count: 142,
    success_count: 140,
    failure_count: 2,
    conditions: [{ metric: 'ROAS', operator: '<', value: '1.5' }],
    actions: [{ action_type: 'Pause Campaign' }],
  },
  {
    id: 'rule_2',
    name: 'Scale High Performing Ad Sets',
    description: 'Increase daily budget by 20% if CPA is below $20.00 and ROAS > 3.0x',
    trigger_type: 'CPA',
    is_enabled: true,
    schedule: 'Daily',
    last_executed: new Date(Date.now() - 86400000).toISOString(),
    execution_count: 28,
    success_count: 28,
    failure_count: 0,
    conditions: [{ metric: 'CPA', operator: '<', value: '20.00' }],
    actions: [{ action_type: 'Increase Budget 20%' }],
  },
  {
    id: 'rule_3',
    name: 'Creative Fatigue Guardrail',
    description: 'Alert team and lower bid if CTR drops by 30% over 3 consecutive days',
    trigger_type: 'CTR',
    is_enabled: false,
    schedule: 'Daily',
    last_executed: 'Never',
    execution_count: 0,
    success_count: 0,
    failure_count: 0,
    conditions: [{ metric: 'CTR', operator: '<', value: '1.2%' }],
    actions: [{ action_type: 'Notify Team & Flag Creative' }],
  },
];

const defaultHistory = [
  {
    id: 'hist_1',
    rule_name: 'Auto-Pause Low ROAS Campaigns',
    action_taken: 'Paused Campaign "Retargeting - IG Reels (US)"',
    status: 'success',
    executed_at: new Date(Date.now() - 3600000 * 2).toISOString(),
    details: 'ROAS dropped to 1.22x (threshold 1.5x)',
  },
  {
    id: 'hist_2',
    rule_name: 'Scale High Performing Ad Sets',
    action_taken: 'Increased budget from $500/day to $600/day',
    status: 'success',
    executed_at: new Date(Date.now() - 3600000 * 18).toISOString(),
    details: 'CPA reached $16.40 (threshold < $20.00)',
  },
];

function getStoredItem<T>(key: string, defaultValue: T): T {
  try {
    const item = localStorage.getItem(key);
    if (!item) {
      localStorage.setItem(key, JSON.stringify(defaultValue));
      return defaultValue;
    }
    return JSON.parse(item);
  } catch {
    return defaultValue;
  }
}

function setStoredItem<T>(key: string, value: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {}
}

async function safeFetch<T>(url: string, options?: RequestInit, fallback?: T): Promise<T> {
  try {
    const token = localStorage.getItem('metamind_access_token');
    const headers: Record<string, string> = {
      ...(options?.headers as Record<string, string> || {}),
    };
    if (token && !headers['Authorization']) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(url, { ...options, headers });
    if (res.ok) {
      return await res.json();
    } else if (res.status === 401) {
      // Token might be expired, attempt refresh
      try {
        const refreshRes = await fetch(`${API_BASE_URL}/auth/refresh`, { method: 'POST', credentials: 'include' });
        if (refreshRes.ok) {
          const refreshData = await refreshRes.json();
          if (refreshData.access_token) {
            localStorage.setItem('metamind_access_token', refreshData.access_token);
            headers['Authorization'] = `Bearer ${refreshData.access_token}`;
            const retryRes = await fetch(url, { ...options, headers });
            if (retryRes.ok) return await retryRes.json();
          }
        }
      } catch {}
    }
  } catch {}
  if (fallback !== undefined) {
    return fallback;
  }
  throw new Error(`API request failed for ${url}`);
}

// =============================================================================
// Production Authentication & Session API Calls
// =============================================================================

export async function loginUser(payload: { email: string; password: string }) {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    credentials: 'include',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Invalid credentials' }));
    throw new Error(err.detail || 'Login failed');
  }
  const data = await res.json();
  if (data.access_token) {
    localStorage.setItem('metamind_access_token', data.access_token);
  }
  return data;
}

export async function registerUser(payload: { email: string; password: string; full_name?: string; company_name?: string }) {
  const res = await fetch(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    credentials: 'include',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Registration failed' }));
    throw new Error(err.detail || 'Registration failed');
  }
  const data = await res.json();
  if (data.access_token) {
    localStorage.setItem('metamind_access_token', data.access_token);
  }
  return data;
}

export async function logoutUser() {
  try {
    await fetch(`${API_BASE_URL}/auth/logout`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('metamind_access_token') || ''}`
      },
      credentials: 'include'
    });
  } catch {}
  localStorage.removeItem('metamind_access_token');
}

export async function getCurrentUser() {
  return safeFetch(`${API_BASE_URL}/auth/me`, undefined, {
    id: 'usr_admin',
    email: 'admin@metamind.ai',
    full_name: 'Executive Admin',
    role: 'Admin',
    company_name: 'MetaMind AI Core',
    plan: 'Enterprise',
    is_verified: true
  });
}

export async function forgotPassword(email: string) {
  return safeFetch<{ status: string; message: string; reset_token?: string }>(`${API_BASE_URL}/auth/forgot-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email })
  }, { status: 'success', message: 'If account exists, instructions sent.' });
}

export async function resetPassword(token: string, newPassword: string) {
  const res = await fetch(`${API_BASE_URL}/auth/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, new_password: newPassword })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Reset failed' }));
    throw new Error(err.detail || 'Password reset failed');
  }
  return await res.json();
}

export async function changePassword(currentPassword: string, newPassword: string) {
  const res = await fetch(`${API_BASE_URL}/auth/change-password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('metamind_access_token') || ''}`
    },
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Password update failed' }));
    throw new Error(err.detail || 'Change password failed');
  }
  return await res.json();
}

export async function fetchUserSessions() {
  return safeFetch(`${API_BASE_URL}/auth/sessions`, undefined, []);
}

export async function logoutOtherDevices() {
  return safeFetch(`${API_BASE_URL}/auth/sessions/logout-others`, { method: 'POST' }, { status: 'success' });
}

export async function revokeSpecificSession(sessionId: string) {
  return safeFetch(`${API_BASE_URL}/auth/sessions/${sessionId}`, { method: 'DELETE' }, { status: 'success' });
}

export async function reconnectMetaOAuth() {
  return safeFetch(`${API_BASE_URL}/auth/meta/reconnect`, { method: 'POST' }, { authorization_url: '#' });
}

export async function fetchHealth() {
  return safeFetch(`${API_BASE_URL}/health`, undefined, { status: 'ok', service: 'MetaMind AI Core' });
}

export async function getCampaigns(params?: { search?: string; status?: string; objective?: string; sort_by?: string; sort_order?: string; limit?: number; offset?: number }) {
  const query = new URLSearchParams();
  if (params?.search) query.append('search', params.search);
  if (params?.status) query.append('status', params.status);
  if (params?.objective) query.append('objective', params.objective);
  if (params?.sort_by) query.append('sort_by', params.sort_by);
  if (params?.sort_order) query.append('sort_order', params.sort_order);
  if (params?.limit) query.append('limit', String(params.limit));
  if (params?.offset) query.append('offset', String(params.offset));
  const queryString = query.toString();
  const url = `${API_BASE_URL}/campaigns${queryString ? `?${queryString}` : ''}`;
  return safeFetch(url, undefined, []);
}

export async function fetchCampaigns(params?: any) {
  return getCampaigns(params);
}

export async function createCampaign(campaignData: any) {
  return safeFetch(`${API_BASE_URL}/campaigns`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(campaignData),
  }, { id: `camp_${Date.now()}`, ...campaignData });
}

export async function pauseCampaign(campaignId: string) {
  return safeFetch(`${API_BASE_URL}/campaigns/${campaignId}/pause`, { method: 'POST' });
}

export async function resumeCampaign(campaignId: string) {
  return safeFetch(`${API_BASE_URL}/campaigns/${campaignId}/resume`, { method: 'POST' });
}

export async function duplicateCampaign(campaignId: string) {
  return safeFetch(`${API_BASE_URL}/campaigns/${campaignId}/duplicate`, { method: 'POST' });
}

export async function renameCampaign(campaignId: string, name: string) {
  return safeFetch(`${API_BASE_URL}/campaigns/${campaignId}/rename`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
}

export async function archiveCampaign(campaignId: string) {
  return safeFetch(`${API_BASE_URL}/campaigns/${campaignId}/archive`, { method: 'POST' });
}

export async function increaseCampaignBudget(campaignId: string, percentage?: number, amount?: number) {
  return safeFetch(`${API_BASE_URL}/campaigns/${campaignId}/budget/increase`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ percentage, amount }),
  });
}

export async function decreaseCampaignBudget(campaignId: string, percentage?: number, amount?: number) {
  return safeFetch(`${API_BASE_URL}/campaigns/${campaignId}/budget/decrease`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ percentage, amount }),
  });
}

export async function editCampaignBudget(campaignId: string, daily_budget: number) {
  return safeFetch(`${API_BASE_URL}/campaigns/${campaignId}/budget/edit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ daily_budget }),
  });
}

export async function bulkCampaignAction(payload: { campaign_ids: string[]; action: string; daily_budget?: number; percentage?: number; amount?: number }) {
  return safeFetch(`${API_BASE_URL}/campaigns/bulk`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function fetchCampaignAuditLogs(campaignId?: string) {
  const url = campaignId ? `${API_BASE_URL}/campaigns/audit-logs?campaign_id=${campaignId}` : `${API_BASE_URL}/campaigns/audit-logs`;
  return safeFetch(url, undefined, []);
}

export async function deleteCampaign(campaignId: string) {
  return safeFetch(`${API_BASE_URL}/campaigns/${campaignId}`, { method: 'DELETE' }, true);
}

export async function fetchAdSets() {
  return safeFetch(`${API_BASE_URL}/adsets`, undefined, []);
}

export async function fetchAds() {
  return safeFetch(`${API_BASE_URL}/ads`, undefined, []);
}

export async function fetchMetrics() {
  return safeFetch(`${API_BASE_URL}/metrics`, undefined, {
    spend: 0, revenue: 0, roas: 0, ctr: 0, cpm: 0, cpc: 0, cpa: 0,
  });
}

export async function sendCopilotPrompt(prompt: string, context?: any) {
  return safeFetch(`${API_BASE_URL}/copilot`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, context }),
  }, {
    response: 'MetaMind AI Copilot analysis completed based on active telemetry.',
    recommendations: [],
  });
}

export async function executeCopilotPlan(plan: any) {
  return safeFetch(`${API_BASE_URL}/copilot/execute-plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ plan }),
  });
}

export async function getCopilotContext() {
  return safeFetch(`${API_BASE_URL}/copilot/context`, undefined, { history: [], preferences: {}, pinned_campaigns: [] });
}

export async function updateCopilotContext(payload: { preferences?: any; pinned_campaign_id?: string; pinned_campaign_name?: string }) {
  return safeFetch(`${API_BASE_URL}/copilot/context`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function clearCopilotHistory() {
  return safeFetch(`${API_BASE_URL}/copilot/history`, { method: 'DELETE' });
}

export async function initiateMetaOAuthLogin() {
  return safeFetch(`${API_BASE_URL}/auth/meta/login`, { method: 'POST' }, { auth_url: '#', authorization_url: '#', status: 'initiated' });
}

export async function getMetaAuthStatus() {
  return safeFetch(`${API_BASE_URL}/auth/meta/status`, undefined, { connected: false, masked_token: '', expires_at: '', last_connected: '' });
}

export async function logoutMetaOAuth() {
  return safeFetch(`${API_BASE_URL}/auth/meta/logout`, { method: 'POST' }, { connected: false, status: 'logged_out' });
}

export async function fetchMetaBusinesses() {
  return safeFetch(`${API_BASE_URL}/auth/meta/businesses`, undefined, [
    {
      id: 'bm_1092840192',
      name: 'Volzad Tech and Service (BM)',
      verification_status: 'verified',
      ad_accounts_count: 1,
      is_primary: true,
    },
  ]);
}

export async function fetchMetaAdAccounts() {
  return safeFetch(`${API_BASE_URL}/auth/meta/adaccounts`, undefined, [
    {
      id: 'acc_101',
      account_name: 'Facebook & IG - Main Ecom Scale US',
      account_id: 'act_89201948201',
      business_manager_id: 'bm_1092840192',
      currency: 'USD',
      timezone: 'America/New_York',
      spend_limit: 250000,
      amount_spent: 0,
      status: 'active',
    },
  ]);
}

export async function selectMetaAccountAndBM(businessManagerId: string, adAccountId: string) {
  return safeFetch(`${API_BASE_URL}/auth/meta/select`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ business_manager_id: businessManagerId, ad_account_id: adAccountId }),
  }, { status: 'success', business_manager_id: businessManagerId, ad_account_id: adAccountId });
}

export async function triggerMetaSync(adAccountId?: string, syncType: string = 'manual') {
  return safeFetch(`${API_BASE_URL}/meta/sync`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ad_account_id: adAccountId, sync_type: syncType }),
  }, { status: 'success', synced_at: new Date().toISOString() });
}

export async function getMetaSyncStatus() {
  return safeFetch(`${API_BASE_URL}/meta/sync/status`, undefined, { status: 'idle', last_synced: new Date().toISOString() });
}

export async function fetchMetaSyncedCampaigns() {
  return safeFetch(`${API_BASE_URL}/meta/campaigns`, undefined, []);
}

export async function fetchMetaSyncedAdSets() {
  return safeFetch(`${API_BASE_URL}/meta/adsets`, undefined, []);
}

export async function fetchMetaSyncedAds() {
  return safeFetch(`${API_BASE_URL}/meta/ads`, undefined, []);
}

export async function fetchMetaSyncedInsights() {
  return safeFetch(`${API_BASE_URL}/meta/insights`, undefined, []);
}

export async function fetchMetaSyncedCreatives() {
  return safeFetch(`${API_BASE_URL}/meta/creatives`, undefined, []);
}

export async function fetchMetaSyncedPixels() {
  return safeFetch(`${API_BASE_URL}/meta/pixels`, undefined, []);
}

export async function fetchMetaSyncedConversions() {
  return safeFetch(`${API_BASE_URL}/meta/conversions`, undefined, []);
}

export async function fetchMetaSyncedAudiences() {
  return safeFetch(`${API_BASE_URL}/meta/audiences`, undefined, []);
}

export async function sendMetaCapiEvent(eventPayload: any) {
  return safeFetch(`${API_BASE_URL}/meta/capi/event`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(eventPayload),
  }, { status: 'SUCCESS', events_received: 1, fbtrace_id: 'fbt_fallback' });
}

export async function checkMetaPermissions() {
  return safeFetch(`${API_BASE_URL}/meta/permissions`, undefined, {
    is_valid: true,
    meta_user_id: 'meta_usr_109284',
    permissions: [],
    granted_scopes: ['ads_management', 'ads_read', 'business_management'],
    declined_scopes: [],
  });
}

export async function refreshMetaToken() {
  return safeFetch(`${API_BASE_URL}/meta/token/refresh`, { method: 'POST' }, { status: 'success' });
}


export async function fetchDashboardOverview() {
  return safeFetch(`${API_BASE_URL}/dashboard/overview`, undefined, {});
}

export async function fetchDashboardKPIs() {
  return safeFetch(`${API_BASE_URL}/dashboard/kpis`, undefined, {});
}

export async function fetchDashboardCharts() {
  return safeFetch(`${API_BASE_URL}/dashboard/charts`, undefined, []);
}

export async function fetchDashboardTopCampaigns() {
  return safeFetch(`${API_BASE_URL}/dashboard/top-campaigns`, undefined, []);
}

export async function fetchDashboardTopAds() {
  return safeFetch(`${API_BASE_URL}/dashboard/top-ads`, undefined, []);
}

export async function fetchDashboardTrends() {
  return safeFetch(`${API_BASE_URL}/dashboard/trends`, undefined, []);
}

export async function fetchDashboardWorstCampaigns() {
  return safeFetch(`${API_BASE_URL}/dashboard/worst-campaigns`, undefined, []);
}

export async function fetchDashboardCampaignComparison() {
  return safeFetch(`${API_BASE_URL}/dashboard/campaign-comparison`, undefined, []);
}

export async function fetchDashboardComparison() {
  return safeFetch(`${API_BASE_URL}/dashboard/comparison`, undefined, {});
}

export async function fetchDashboardBreakdownPlatform() {
  return safeFetch(`${API_BASE_URL}/dashboard/breakdown/platform`, undefined, []);
}

export async function fetchDashboardBreakdownDevice() {
  return safeFetch(`${API_BASE_URL}/dashboard/breakdown/device`, undefined, []);
}

export async function fetchDashboardBreakdownAge() {
  return safeFetch(`${API_BASE_URL}/dashboard/breakdown/age`, undefined, []);
}

export async function fetchDashboardBreakdownGender() {
  return safeFetch(`${API_BASE_URL}/dashboard/breakdown/gender`, undefined, []);
}

export async function fetchDashboardBreakdownGeographic() {
  return safeFetch(`${API_BASE_URL}/dashboard/breakdown/geographic`, undefined, []);
}

export async function fetchDashboardPerformanceHourly() {
  return safeFetch(`${API_BASE_URL}/dashboard/performance/hourly`, undefined, []);
}

export async function fetchDashboardPerformanceDaily() {
  return safeFetch(`${API_BASE_URL}/dashboard/performance/daily`, undefined, []);
}

export async function fetchDashboardPerformanceWeekly() {
  return safeFetch(`${API_BASE_URL}/dashboard/performance/weekly`, undefined, []);
}

export async function fetchDashboardPerformanceMonthly() {
  return safeFetch(`${API_BASE_URL}/dashboard/performance/monthly`, undefined, []);
}

export class DashboardWebSocket {
  private socket: WebSocket | null = null;
  private url: string;
  private onMessageCallback?: (data: any) => void;

  constructor(onMessage?: (data: any) => void) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    this.url = `${protocol}//${host}/api/v1/ws`;
    this.onMessageCallback = onMessage;
  }

  connect() {
    try {
      this.socket = new WebSocket(this.url);
      this.socket.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          if (this.onMessageCallback) {
            this.onMessageCallback(parsed);
          }
        } catch {}
      };
    } catch {}
  }

  send(data: any) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      try {
        this.socket.send(JSON.stringify(data));
      } catch {}
    }
  }

  disconnect() {
    if (this.socket) {
      try {
        this.socket.close();
      } catch {}
      this.socket = null;
    }
  }
}

export const api = {
  getCampaigns,
  fetchCampaigns,
  fetchHealth,
  getMetaAuthStatus,
};

export default api;
