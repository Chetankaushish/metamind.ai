import {
  MetaBusinessManager,
  MetaAdAccount,
  MetaTokenInfo,
  SaaSUser
} from '../types';

export const initialBusinessManagers: MetaBusinessManager[] = [];

export const initialAdAccounts: MetaAdAccount[] = [];

export const initialTokenInfo: MetaTokenInfo = {
  tokenType: 'long_lived_user',
  accessTokenMasked: '',
  scopes: [
    'ads_management',
    'ads_read',
    'business_management',
    'pages_read_engagement',
    'instagram_basic',
    'leads_retrieval'
  ],
  expiresAt: '',
  isValid: false,
  lastRefreshed: 'Never Connected'
};

export const currentSaaSUser: SaaSUser = {
  fullName: 'Admin User',
  email: 'admin@system.local',
  role: 'Admin',
  avatarUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
  companyName: 'No organization configured',
  plan: 'Billing not configured'
};
