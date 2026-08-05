import React, { useState, useEffect, Suspense, lazy } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Header } from './components/common/Header';
import { Sidebar, NavTab } from './components/common/Sidebar';
import { Lock, Facebook, Sparkles, Shield, User, LogIn, LogOut } from 'lucide-react';
import { AuthModal } from './components/auth/AuthModal';
import { SessionManagerModal } from './components/auth/SessionManagerModal';
import { FacebookOAuthModal } from './components/auth/FacebookOAuthModal';
import { useAuth } from './contexts/AuthContext';

const DashboardView = lazy(() => import('./components/dashboard/DashboardView').then(m => ({ default: m.DashboardView })));
const CampaignsView = lazy(() => import('./components/campaigns/CampaignsView').then(m => ({ default: m.CampaignsView })));
const CopilotView = lazy(() => import('./components/copilot/CopilotView').then(m => ({ default: m.CopilotView })));

const ViewLoader = () => (
  <div className="flex items-center justify-center min-h-[400px]">
    <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
  </div>
);

import {
  Campaign,
  MetaAdSet,
  MetaAd,
  MetricSummary
} from './types';

import {
  initialBusinessManagers,
  initialAdAccounts,
  initialTokenInfo,
  currentSaaSUser
} from './constants';

import {
  fetchCampaigns,
  DashboardWebSocket,
  fetchHealth,
  getMetaAuthStatus,
  initiateMetaOAuthLogin
} from './services/api';

export default function App() {
  const { user, isAuthenticated, logout } = useAuth();
  const [activeTab, setActiveTab] = useState<NavTab>('dashboard');
  const [activePlatformTab, setActivePlatformTab] = useState<string>('overview');
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState<boolean>(false);
  const [isFacebookOAuthModalOpen, setIsFacebookOAuthModalOpen] = useState<boolean>(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);
  const [isSessionModalOpen, setIsSessionModalOpen] = useState<boolean>(false);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [isSyncing, setIsSyncing] = useState<boolean>(false);

  const [isMetaConnected, setIsMetaConnected] = useState<boolean>(false);
  const [businessManagers, setBusinessManagers] = useState(initialBusinessManagers);
  const [selectedBm, setSelectedBm] = useState(initialBusinessManagers[0]);
  const [adAccounts, setAdAccounts] = useState(initialAdAccounts);
  const [selectedAccount, setSelectedAccount] = useState(initialAdAccounts[0]);
  const [tokenInfo, setTokenInfo] = useState(initialTokenInfo);

  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [adSets, setAdSets] = useState<MetaAdSet[]>([]);
  const [ads, setAds] = useState<MetaAd[]>([]);
  const [notifications, setNotifications] = useState<any[]>([]);

  const handleConnectMeta = async () => {
    try {
      const res = await initiateMetaOAuthLogin();
      if (res.authorization_url && res.authorization_url !== '#') {
        window.open(res.authorization_url, 'MetaLogin', 'width=600,height=700');
      } else {
        setIsFacebookOAuthModalOpen(true);
      }
    } catch {
      setIsFacebookOAuthModalOpen(true);
    }
  };

  useEffect(() => {
    const ws = new DashboardWebSocket((message) => {
      if (message.event === 'campaign_update' || message.event === 'sync_complete') {
        fetchCampaigns().then((data) => {
          if (Array.isArray(data)) setCampaigns(data);
        }).catch(() => {});
      }
    });
    ws.connect();
    return () => ws.disconnect();
  }, []);

  useEffect(() => {
    getMetaAuthStatus()
      .then((status) => {
        if (status && status.connected) {
          setIsMetaConnected(true);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    fetchHealth().catch(() => {});
    if (isMetaConnected) {
      fetchCampaigns()
        .then((data) => {
          if (Array.isArray(data)) setCampaigns(data);
        })
        .catch(() => {});
    }
  }, [isMetaConnected]);

  const calculatedMetrics: MetricSummary = React.useMemo(() => {
    if (!isMetaConnected || campaigns.length === 0) {
      return {
        spend: 0, spendChange: 0, revenue: 0, revenueChange: 0, roas: 0, roasChange: 0,
        ctr: 0, ctrChange: 0, cpm: 0, cpc: 0, cpa: 0, cpaChange: 0, reach: 0, impressions: 0,
        frequency: 0, clicks: 0, purchases: 0, leads: 0, costPerResult: 0, budget: 0,
        campaignStatus: 'paused', learningPhaseStatus: 'learning', adFatigueScore: 0,
        audienceSaturation: 0, pixelHealth: 'warning', conversionApiHealth: 'warning'
      };
    }
    const totalSpend = campaigns.reduce((acc, c) => acc + (c.spend || 0), 0);
    const totalRevenue = campaigns.reduce((acc, c) => acc + (c.revenue || 0), 0);
    const totalPurchases = campaigns.reduce((acc, c) => acc + (c.purchases || 0), 0);
    const totalClicks = campaigns.reduce((acc, c) => acc + (c.clicks || 0), 0);
    const totalImpressions = campaigns.reduce((acc, c) => acc + (c.impressions || 0), 0);
    const totalReach = campaigns.reduce((acc, c) => acc + (c.reach || 0), 0);
    const totalLeads = campaigns.reduce((acc, c) => acc + (c.leads || 0), 0);
    const avgRoas = totalSpend > 0 ? Number((totalRevenue / totalSpend).toFixed(2)) : 0;
    const avgCpa = totalPurchases > 0 ? Number((totalSpend / totalPurchases).toFixed(2)) : 0;
    const avgCtr = totalImpressions > 0 ? Number(((totalClicks / totalImpressions) * 100).toFixed(2)) : 0;
    const avgCpm = totalImpressions > 0 ? Number(((totalSpend / totalImpressions) * 1000).toFixed(2)) : 0;
    const avgCpc = totalClicks > 0 ? Number((totalSpend / totalClicks).toFixed(2)) : 0;
    const avgFreq = totalReach > 0 ? Number((totalImpressions / totalReach).toFixed(2)) : 0;

    return {
      spend: totalSpend, spendChange: 0, revenue: totalRevenue, revenueChange: 0,
      roas: avgRoas, roasChange: 0, ctr: avgCtr, ctrChange: 0, cpm: avgCpm, cpc: avgCpc,
      cpa: avgCpa, cpaChange: 0, reach: totalReach, impressions: totalImpressions, frequency: avgFreq,
      clicks: totalClicks, purchases: totalPurchases, leads: totalLeads, costPerResult: avgCpa,
      budget: campaigns.reduce((acc, c) => acc + (c.dailyBudget || 0), 0),
      campaignStatus: 'active', learningPhaseStatus: 'passed', adFatigueScore: 0,
      audienceSaturation: 0, pixelHealth: 'optimal', conversionApiHealth: 'optimal'
    };
  }, [isMetaConnected, campaigns]);

  const renderLockedFeature = (featureName: string) => (
    <div className="w-full max-w-2xl mx-auto my-12 p-8 sm:p-10 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl text-center space-y-4">
      <div className="w-14 h-14 rounded-2xl bg-amber-500/10 text-amber-600 border border-amber-500/30 flex items-center justify-center mx-auto shadow-xs">
        <Lock className="w-7 h-7" />
      </div>
      <div className="space-y-1.5">
        <h2 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-slate-100">
          {featureName} is Locked
        </h2>
        <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto leading-relaxed">
          Connect your Meta Business Account to unlock this feature.
        </p>
      </div>
      <div className="pt-2">
        <button
          onClick={() => setIsFacebookOAuthModalOpen(true)}
          className="h-10 px-6 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs shadow-md shadow-blue-500/20 inline-flex items-center gap-2 transition"
        >
          <Facebook className="w-4 h-4 fill-current" />
          <span>Connect Meta Account</span>
        </button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex font-sans transition-colors duration-200 selection:bg-blue-600 selection:text-white overflow-x-hidden">
      <Sidebar
        activeTab={activeTab}
        setActiveTab={(tab) => setActiveTab(tab)}
        collapsed={sidebarCollapsed}
        setCollapsed={setSidebarCollapsed}
        alertCount={0}
        isMetaConnected={isMetaConnected}
        user={user ? {
          fullName: user.full_name,
          email: user.email,
          role: user.role,
          avatarUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
          companyName: user.company_name || 'MetaMind AI Core',
          plan: user.plan || 'Enterprise'
        } : currentSaaSUser}
        onOpenFacebookOAuthModal={handleConnectMeta}
        onOpenAuthModal={() => setIsAuthModalOpen(true)}
        onOpenSessionModal={() => setIsSessionModalOpen(true)}
      />

      <div className={`flex-1 flex flex-col min-w-0 min-h-screen transition-all duration-300 ${sidebarCollapsed ? 'pl-16' : 'pl-64'}`}>
        <Header
          darkMode={theme === 'dark'}
          setDarkMode={(val) => setTheme(val ? 'dark' : 'light')}
          theme={theme}
          toggleTheme={() => setTheme(t => t === 'dark' ? 'light' : 'dark')}
          isSyncing={isSyncing}
          onManualSync={() => setIsSyncing(true)}
          user={currentSaaSUser}
          onOpenCopilot={() => setActiveTab('copilot')}
          onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
          activePlatformTab={activePlatformTab}
          setActivePlatformTab={setActivePlatformTab}
          activeTab={activeTab}
          notifications={notifications}
          setNotifications={setNotifications}
          isMetaConnected={isMetaConnected}
          setIsMetaConnected={setIsMetaConnected}
          businessManagers={businessManagers}
          selectedBm={selectedBm}
          setSelectedBm={setSelectedBm}
          adAccounts={adAccounts}
          selectedAccount={selectedAccount}
          setSelectedAccount={setSelectedAccount}
          tokenInfo={tokenInfo}
          onOpenFacebookOAuthModal={() => setIsFacebookOAuthModalOpen(true)}
        />

        <main className="flex-1 p-4 lg:p-6 overflow-y-auto">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25, ease: 'easeInOut' }}
            >
              <Suspense fallback={<ViewLoader />}>
                {activeTab === 'campaigns' ? (
                  <CampaignsView
                    isMetaConnected={isMetaConnected}
                    onOpenFacebookOAuthModal={() => setIsFacebookOAuthModalOpen(true)}
                    campaigns={campaigns}
                    onRefreshCampaigns={() => {
                      fetchCampaigns().then(res => { if (Array.isArray(res)) setCampaigns(res); });
                    }}
                  />
                ) : activeTab === 'copilot' ? (
                  <CopilotView
                    isMetaConnected={isMetaConnected}
                    onOpenFacebookOAuthModal={() => setIsFacebookOAuthModalOpen(true)}
                  />
                ) : (
                  <DashboardView
                    isMetaConnected={isMetaConnected}
                    onOpenFacebookOAuthModal={() => setIsFacebookOAuthModalOpen(true)}
                    selectedAccount={selectedAccount}
                    metrics={calculatedMetrics}
                    campaigns={campaigns}
                    adSets={adSets}
                    ads={ads}
                    onOpenCopilot={() => setActiveTab('copilot')}
                    onNavigateTab={(tab) => setActiveTab(tab as NavTab)}
                  />
                )}
              </Suspense>
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />

      <SessionManagerModal
        isOpen={isSessionModalOpen}
        onClose={() => setIsSessionModalOpen(false)}
      />

      <FacebookOAuthModal
        isOpen={isFacebookOAuthModalOpen}
        onClose={() => setIsFacebookOAuthModalOpen(false)}
        onSyncComplete={() => {
          setIsMetaConnected(true);
          fetchCampaigns().then(res => { if (Array.isArray(res)) setCampaigns(res); });
          setActiveTab('dashboard');
        }}
      />
    </div>
  );
}
