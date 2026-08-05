import React, { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import {
  DollarSign,
  TrendingUp,
  Target,
  MousePointer,
  Activity,
  Layers,
  Sparkles,
  Zap,
  ArrowUpRight,
  ArrowDownRight,
  CheckCircle2,
  AlertTriangle,
  BarChart2,
  Facebook,
  Instagram,
  Key,
  Palette,
  ChevronRight,
  Filter,
  Calendar,
  Globe,
  Smartphone,
  Users,
  Clock,
  PieChart as PieChartIcon,
  RefreshCw,
  Award,
  TrendingDown
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  CartesianGrid
} from 'recharts';
import { MetricSummary, Campaign, MetaAdSet, MetaAd, CreativeAsset, MetaAdAccount, MetaBusinessManager, MetaTokenInfo } from '../../types';
import {
  fetchDashboardKPIs,
  fetchDashboardCharts,
  fetchDashboardTopCampaigns,
  fetchDashboardWorstCampaigns,
  fetchDashboardCampaignComparison,
  fetchDashboardBreakdownPlatform,
  fetchDashboardBreakdownDevice,
  fetchDashboardBreakdownAge,
  fetchDashboardBreakdownGender,
  fetchDashboardBreakdownGeographic,
  fetchDashboardPerformanceDaily,
  fetchDashboardPerformanceHourly,
  fetchDashboardPerformanceWeekly,
  fetchDashboardPerformanceMonthly
} from '../../services/api';

interface DashboardViewProps {
  isMetaConnected: boolean;
  onOpenFacebookOAuthModal: () => void;
  selectedAccount: MetaAdAccount;
  selectedBm?: MetaBusinessManager;
  tokenInfo?: MetaTokenInfo;
  metrics?: MetricSummary;
  campaigns?: Campaign[];
  adSets?: MetaAdSet[];
  ads?: MetaAd[];
  creatives?: CreativeAsset[];
  onOpenCopilot?: () => void;
  onRunAgents?: () => void;
  onNavigateTab?: (tab: string) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  isMetaConnected,
  onOpenFacebookOAuthModal,
  selectedAccount,
  selectedBm,
  tokenInfo,
  metrics,
  campaigns = [],
  creatives = [],
  onOpenCopilot,
  onRunAgents,
  onNavigateTab
}) => {
  const [timeRange, setTimeRange] = useState<string>('last_30_days');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [activeBreakdownTab, setActiveBreakdownTab] = useState<'platform' | 'device' | 'age' | 'gender' | 'geo'>('platform');
  const [granularity, setGranularity] = useState<'daily' | 'hourly' | 'weekly' | 'monthly'>('daily');

  const [loading, setLoading] = useState<boolean>(false);
  const [kpiData, setKpiData] = useState<any>(null);
  const [breakdownData, setBreakdownData] = useState<any[]>([]);
  const [timePerformanceData, setTimePerformanceData] = useState<any[]>([]);
  const [comparisonList, setComparisonList] = useState<any[]>([]);
  const [worstList, setWorstList] = useState<any[]>([]);

  useEffect(() => {
    async function loadDashboardEngineData() {
      if (!isMetaConnected) return;
      setLoading(true);
      try {
        const [kpis, comparison, worst] = await Promise.all([
          fetchDashboardKPIs(),
          fetchDashboardCampaignComparison(),
          fetchDashboardWorstCampaigns()
        ]);
        if (kpis && !('error' in kpis)) setKpiData(kpis);
        if (Array.isArray(comparison)) setComparisonList(comparison);
        if (Array.isArray(worst)) setWorstList(worst);
      } catch (err) {
        console.error("Failed to load dashboard aggregation engine data:", err);
      } finally {
        setLoading(false);
      }
    }
    loadDashboardEngineData();
  }, [isMetaConnected, timeRange, statusFilter]);

  useEffect(() => {
    async function loadBreakdown() {
      if (!isMetaConnected) return;
      try {
        let res: any[] = [];
        if (activeBreakdownTab === 'platform') res = await fetchDashboardBreakdownPlatform();
        else if (activeBreakdownTab === 'device') res = await fetchDashboardBreakdownDevice();
        else if (activeBreakdownTab === 'age') res = await fetchDashboardBreakdownAge();
        else if (activeBreakdownTab === 'gender') res = await fetchDashboardBreakdownGender();
        else if (activeBreakdownTab === 'geo') res = await fetchDashboardBreakdownGeographic();
        if (Array.isArray(res)) setBreakdownData(res);
      } catch (err) {
        console.error("Failed to load breakdown:", err);
      }
    }
    loadBreakdown();
  }, [isMetaConnected, activeBreakdownTab]);

  useEffect(() => {
    async function loadTimePerformance() {
      if (!isMetaConnected) return;
      try {
        let res: any[] = [];
        if (granularity === 'hourly') res = await fetchDashboardPerformanceHourly();
        else if (granularity === 'daily') res = await fetchDashboardPerformanceDaily();
        else if (granularity === 'weekly') res = await fetchDashboardPerformanceWeekly();
        else if (granularity === 'monthly') res = await fetchDashboardPerformanceMonthly();
        if (Array.isArray(res)) setTimePerformanceData(res);
      } catch (err) {
        console.error("Failed to load time performance:", err);
      }
    }
    loadTimePerformance();
  }, [isMetaConnected, granularity]);

  const dataMetrics: MetricSummary = metrics || {
    spend: kpiData?.spend || 0,
    spendChange: kpiData?.spendChange || 0,
    revenue: kpiData?.revenue || 0,
    revenueChange: kpiData?.revenueChange || 0,
    roas: kpiData?.roas || 0,
    roasChange: kpiData?.roasChange || 0,
    ctr: kpiData?.ctr || 0,
    ctrChange: kpiData?.ctrChange || 0,
    cpm: kpiData?.cpm || 0,
    cpc: kpiData?.cpc || 0,
    cpa: kpiData?.cpa || 0,
    cpaChange: kpiData?.cpaChange || 0,
    reach: kpiData?.reach || 0,
    impressions: kpiData?.impressions || 0,
    frequency: kpiData?.frequency || 0,
    clicks: kpiData?.clicks || 0,
    purchases: kpiData?.purchases || 0,
    leads: kpiData?.leads || 0,
    costPerResult: kpiData?.cpa || 0,
    budget: kpiData?.budget || 0,
    campaignStatus: campaigns.length > 0 ? 'active' : 'paused',
    learningPhaseStatus: campaigns.length > 0 ? 'passed' : 'learning',
    adFatigueScore: 0,
    audienceSaturation: 0,
    pixelHealth: isMetaConnected ? 'optimal' : 'warning',
    conversionApiHealth: isMetaConnected ? 'optimal' : 'warning'
  };

  const COLORS = ['#6366f1', '#ec4899', '#3b82f6', '#10b981', '#8b5cf6'];

  if (!isMetaConnected) {
    return (
      <div className="w-full max-w-[1700px] mx-auto space-y-6">
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="text-center space-y-1.5 pt-0.5"
        >
          <div className="inline-flex items-center gap-2 px-3 py-0.5 rounded-full bg-blue-50 dark:bg-blue-950/60 border border-blue-200/80 dark:border-blue-800/80 text-blue-700 dark:text-blue-300 text-[11px] font-semibold shadow-2xs">
            <Facebook className="w-3.5 h-3.5 fill-current text-blue-600 dark:text-blue-400 shrink-0" />
            <span>Meta Marketing Partner API v21.0 Integration</span>
          </div>

          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
            Connect Meta Business Account
          </h1>

          <p className="max-w-xl mx-auto text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
            Unlock real-time Facebook & Instagram ad telemetry, Advantage+ AI budget optimization, and instant Conversions API signal tracking.
          </p>
        </motion.div>

        <div className="relative">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 relative z-10">
            {[
              { step: '01', title: 'Connect Business Manager', desc: 'Authenticate securely via Meta OAuth 2.0 or System User Token.', status: 'Ready', active: true },
              { step: '02', title: 'Select Ad Account', desc: 'Choose your target Facebook or Instagram ad account.', status: 'Pending', active: false },
              { step: '03', title: 'Sync Campaigns & Pixel', desc: 'Import active campaigns, ad sets, creatives, and CAPI signals.', status: 'Pending', active: false },
              { step: '04', title: 'Live Telemetry Dashboard', desc: 'Monitor ROAS, CPA, CTR, and AI Copilot recommendations.', status: 'Pending', active: false }
            ].map((s, idx) => (
              <motion.div
                key={s.step}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05, duration: 0.25 }}
                className={`p-4 rounded-2xl border backdrop-blur-xl flex flex-col justify-between h-full ${
                  s.active
                    ? 'bg-white dark:bg-slate-900 border-indigo-500/80 shadow-lg shadow-indigo-500/10'
                    : 'bg-white/80 dark:bg-slate-900/80 border-slate-200/50 dark:border-slate-800/50'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between mb-2.5">
                    <span className="text-xs font-mono font-extrabold px-2.5 py-0.5 rounded-lg border bg-indigo-600 text-white border-indigo-500">
                      Step {s.step}
                    </span>
                    <span className="text-[10px] font-extrabold px-2.5 py-0.5 rounded-full border bg-emerald-500/15 text-emerald-600 border-emerald-500/30">
                      {s.status}
                    </span>
                  </div>
                  <h3 className="text-sm font-bold mb-1 text-indigo-600 dark:text-indigo-400">
                    {s.title}
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">{s.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.99 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3, delay: 0.1 }}
          className="p-5 rounded-3xl bg-slate-900 text-white shadow-xl border border-slate-800 relative overflow-hidden text-center space-y-3.5"
        >
          <div className="w-11 h-11 rounded-2xl bg-blue-600 flex items-center justify-center mx-auto shadow-md shadow-blue-500/20 shrink-0">
            <Facebook className="w-5 h-5 text-white fill-current" />
          </div>

          <div className="max-w-md mx-auto space-y-1">
            <h2 className="text-lg font-bold tracking-tight text-white">
              Ready to sync your Meta Ads?
            </h2>
            <p className="text-xs text-slate-300 leading-relaxed">
              Connect your Meta Business account to launch real-time AI optimization.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-2.5 max-w-md mx-auto">
            <button
              onClick={onOpenFacebookOAuthModal}
              className="w-full sm:w-auto h-10 px-6 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs shadow-md shadow-blue-500/20 flex items-center justify-center gap-2 transition cursor-pointer"
            >
              <Facebook className="w-4 h-4 fill-current" />
              <span>Connect Meta Account</span>
              <ChevronRight className="w-4 h-4 ml-0.5" />
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-[1700px] mx-auto space-y-5">
      {/* Header Banner */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-5 rounded-3xl bg-gradient-to-r from-slate-900 via-blue-950 to-indigo-950 text-white shadow-xl border border-blue-500/20 relative overflow-hidden"
      >
        <div className="relative z-10 space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px] font-bold uppercase tracking-wider flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              Meta Marketing API v21.0 Active
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-extrabold tracking-tight flex items-center gap-2">
            <Facebook className="w-6 h-6 text-blue-400 fill-current shrink-0" />
            Meta Analytics & Performance Engine
          </h1>
        </div>

        {/* Filters Controls */}
        <div className="flex flex-wrap items-center gap-2.5 z-10">
          <div className="flex items-center gap-1.5 bg-slate-800/80 border border-slate-700/80 px-2.5 py-1.5 rounded-xl text-xs font-semibold text-slate-200">
            <Calendar className="w-3.5 h-3.5 text-indigo-400" />
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              className="bg-transparent text-white outline-none cursor-pointer"
            >
              <option value="today" className="bg-slate-900 text-white">Today</option>
              <option value="yesterday" className="bg-slate-900 text-white">Yesterday</option>
              <option value="last_7_days" className="bg-slate-900 text-white">Last 7 Days</option>
              <option value="last_30_days" className="bg-slate-900 text-white">Last 30 Days</option>
              <option value="last_90_days" className="bg-slate-900 text-white">Last 90 Days</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5 bg-slate-800/80 border border-slate-700/80 px-2.5 py-1.5 rounded-xl text-xs font-semibold text-slate-200">
            <Filter className="w-3.5 h-3.5 text-pink-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-transparent text-white outline-none cursor-pointer"
            >
              <option value="all" className="bg-slate-900 text-white">All Statuses</option>
              <option value="active" className="bg-slate-900 text-white">ACTIVE Only</option>
              <option value="paused" className="bg-slate-900 text-white">PAUSED Only</option>
            </select>
          </div>
        </div>
      </motion.div>

      {/* Executive KPI Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3 sm:gap-3.5">
        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-xs relative overflow-hidden">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Ad Spend</span>
            <DollarSign className="w-4 h-4 text-blue-500" />
          </div>
          <p className="text-lg font-extrabold text-slate-900 dark:text-slate-100 mt-2">
            ${dataMetrics.spend.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </p>
          <div className="flex items-center gap-1 mt-1 text-[11px] font-bold text-emerald-600 dark:text-emerald-400">
            <ArrowUpRight className="w-3 h-3" />
            <span>+{dataMetrics.spendChange}% vs prev</span>
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Ad Revenue</span>
            <TrendingUp className="w-4 h-4 text-emerald-500" />
          </div>
          <p className="text-lg font-extrabold text-slate-900 dark:text-slate-100 mt-2">
            ${dataMetrics.revenue.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </p>
          <div className="flex items-center gap-1 mt-1 text-[11px] font-bold text-emerald-600 dark:text-emerald-400">
            <ArrowUpRight className="w-3 h-3" />
            <span>+{dataMetrics.revenueChange}% vs prev</span>
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Meta ROAS</span>
            <Target className="w-4 h-4 text-indigo-500" />
          </div>
          <p className="text-lg font-extrabold text-indigo-600 dark:text-indigo-400 mt-2">
            {dataMetrics.roas}x
          </p>
          <div className="flex items-center gap-1 mt-1 text-[11px] font-bold text-emerald-600 dark:text-emerald-400">
            <ArrowUpRight className="w-3 h-3" />
            <span>+{dataMetrics.roasChange}% growth</span>
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Click Rate (CTR)</span>
            <MousePointer className="w-4 h-4 text-pink-500" />
          </div>
          <p className="text-lg font-extrabold text-slate-900 dark:text-slate-100 mt-2">
            {dataMetrics.ctr}%
          </p>
          <div className="flex items-center gap-1 mt-1 text-[11px] font-bold text-emerald-600 dark:text-emerald-400">
            <ArrowUpRight className="w-3 h-3" />
            <span>+{dataMetrics.ctrChange}%</span>
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>CPA Cost</span>
            <Activity className="w-4 h-4 text-purple-500" />
          </div>
          <p className="text-lg font-extrabold text-slate-900 dark:text-slate-100 mt-2">
            ${dataMetrics.cpa}
          </p>
          <div className="flex items-center gap-1 mt-1 text-[11px] font-bold text-emerald-600 dark:text-emerald-400">
            <ArrowDownRight className="w-3 h-3" />
            <span>{dataMetrics.cpaChange}% cost efficiency</span>
          </div>
        </div>

        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>CPM Rate</span>
            <BarChart2 className="w-4 h-4 text-amber-500" />
          </div>
          <p className="text-lg font-extrabold text-slate-900 dark:text-slate-100 mt-2">
            ${dataMetrics.cpm}
          </p>
          <span className="text-[10px] text-slate-400 mt-1 block font-medium">Per 1k impressions</span>
        </div>

        <div className="p-4 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
            <span>Purchases</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <p className="text-lg font-extrabold text-slate-900 dark:text-slate-100 mt-2">
            {dataMetrics.purchases}
          </p>
          <span className="text-[10px] text-emerald-600 dark:text-emerald-400 mt-1 block font-bold">Verified Conversions</span>
        </div>
      </div>

      {/* Main Charts & Breakdown Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Time Series Performance Chart */}
        <div className="lg:col-span-2 p-5 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <Clock className="w-4 h-4 text-indigo-500" />
                Performance Trends & Scale Engine
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">Aggregated spend vs revenue trajectory</p>
            </div>

            {/* Granularity Selector */}
            <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 p-1 rounded-xl">
              {(['hourly', 'daily', 'weekly', 'monthly'] as const).map((g) => (
                <button
                  key={g}
                  onClick={() => setGranularity(g)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-semibold capitalize transition ${
                    granularity === g
                      ? 'bg-indigo-600 text-white shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                  }`}
                >
                  {g}
                </button>
              ))}
            </div>
          </div>

          <div className="h-[280px] w-full flex items-center justify-center">
            {timePerformanceData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={timePerformanceData}>
                  <defs>
                    <linearGradient id="spendGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0}/>
                    </linearGradient>
                    <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0.0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                  <XAxis dataKey="period" stroke="#94a3b8" fontSize={11} />
                  <YAxis stroke="#94a3b8" fontSize={11} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '12px', color: '#fff', fontSize: '12px' }}
                  />
                  <Area type="monotone" dataKey="spend" name="Spend ($)" stroke="#3b82f6" fillOpacity={1} fill="url(#spendGrad)" strokeWidth={2} />
                  <Area type="monotone" dataKey="revenue" name="Revenue ($)" stroke="#10b981" fillOpacity={1} fill="url(#revGrad)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center text-xs text-slate-400 py-12">
                No performance telemetry available for this period.
              </div>
            )}
          </div>
        </div>

        {/* Breakdown Dimension Card */}
        <div className="p-5 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <PieChartIcon className="w-4 h-4 text-pink-500" />
                Audience & Placement Breakdown
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">Demographic & placement distribution</p>
            </div>
          </div>

          {/* Breakdown Tabs */}
          <div className="flex flex-wrap gap-1 bg-slate-100 dark:bg-slate-800 p-1 rounded-xl text-xs font-semibold">
            {[
              { id: 'platform', label: 'Platform' },
              { id: 'device', label: 'Device' },
              { id: 'age', label: 'Age' },
              { id: 'gender', label: 'Gender' },
              { id: 'geo', label: 'Geo' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveBreakdownTab(tab.id as any)}
                className={`px-2.5 py-1 rounded-lg transition capitalize cursor-pointer ${
                  activeBreakdownTab === tab.id
                    ? 'bg-indigo-600 text-white shadow-xs font-bold'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="space-y-3 pt-1">
            {breakdownData.length > 0 ? (
              breakdownData.map((item, idx) => (
                <div key={idx} className="space-y-1">
                  <div className="flex items-center justify-between text-xs font-semibold">
                    <span className="text-slate-800 dark:text-slate-200">{item.label}</span>
                    <span className="text-indigo-600 dark:text-indigo-400 font-bold">{item.percentage}% ({item.roas}x ROAS)</span>
                  </div>
                  <div className="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-indigo-500 to-pink-500 rounded-full transition-all duration-500"
                      style={{ width: `${item.percentage}%` }}
                    />
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center text-xs text-slate-400 py-8">
                No breakdown data available.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Campaign Comparison Table & Top/Worst Performers */}
      <div className="p-5 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <Award className="w-4 h-4 text-emerald-500" />
              Campaign Performance Comparison Engine
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">Side-by-side metric comparison across synced Meta campaigns</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-extrabold uppercase text-slate-400 tracking-wider">
                <th className="py-3 px-3">Campaign Name</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-3 text-right">Spend</th>
                <th className="py-3 px-3 text-right">Revenue</th>
                <th className="py-3 px-3 text-right">ROAS</th>
                <th className="py-3 px-3 text-right">CPA</th>
                <th className="py-3 px-3 text-right">CTR</th>
                <th className="py-3 px-3 text-right">ROAS vs Avg</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
              {comparisonList.length > 0 ? (
                comparisonList.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition">
                    <td className="py-3 px-3 font-bold text-slate-900 dark:text-slate-100">{c.name}</td>
                    <td className="py-3 px-3">
                      <span className="px-2 py-0.5 rounded-md text-[10px] font-extrabold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                        {c.status}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-right font-semibold">${c.spend.toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
                    <td className="py-3 px-3 text-right font-semibold text-emerald-600 dark:text-emerald-400">${c.revenue.toLocaleString('en-US', { minimumFractionDigits: 2 })}</td>
                    <td className="py-3 px-3 text-right font-bold text-indigo-600 dark:text-indigo-400">{c.roas}x</td>
                    <td className="py-3 px-3 text-right font-medium">${c.cpa}</td>
                    <td className="py-3 px-3 text-right font-medium">{c.ctr}%</td>
                    <td className="py-3 px-3 text-right font-extrabold">
                      <span className={`inline-flex items-center gap-0.5 ${c.roas_delta_pct >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-500'}`}>
                        {c.roas_delta_pct >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                        {c.roas_delta_pct}%
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-400">
                    No Meta campaigns found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default DashboardView;
