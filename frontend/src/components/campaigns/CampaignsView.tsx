import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Search, Filter, Plus, ArrowUpDown, ChevronLeft, ChevronRight,
  Play, Pause, Copy, Edit3, Archive, TrendingUp, TrendingDown, DollarSign,
  CheckSquare, Square, AlertTriangle, ShieldCheck, History, RefreshCw, X, Check
} from 'lucide-react';
import { Campaign } from '../../types';
import {
  getCampaigns, pauseCampaign, resumeCampaign, duplicateCampaign,
  renameCampaign, archiveCampaign, increaseCampaignBudget, decreaseCampaignBudget,
  editCampaignBudget, bulkCampaignAction, fetchCampaignAuditLogs, deleteCampaign
} from '../../services/api';

interface CampaignsViewProps {
  isMetaConnected: boolean;
  onOpenFacebookOAuthModal: () => void;
  campaigns?: Campaign[];
  onRefreshCampaigns?: () => void;
}

export const CampaignsView: React.FC<CampaignsViewProps> = ({
  isMetaConnected,
  onOpenFacebookOAuthModal,
  campaigns: initialCampaigns = [],
  onRefreshCampaigns
}) => {
  // Campaign State & Filtering
  const [campaigns, setCampaigns] = useState<Campaign[]>(initialCampaigns);
  const [loading, setLoading] = useState<boolean>(false);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [objectiveFilter, setObjectiveFilter] = useState<string>('ALL');
  const [sortBy, setSortBy] = useState<string>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState<number>(1);
  const limit = 10;

  // Selection & Bulk State
  const [selectedCampaignIds, setSelectedCampaignIds] = useState<string[]>([]);

  // Confirmation Modal State
  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean;
    title: string;
    description: string;
    actionType: string;
    targetId?: string;
    payload?: any;
    isDangerous?: boolean;
  }>({
    isOpen: false,
    title: '',
    description: '',
    actionType: ''
  });

  // Action Loading & Optimistic Backup State
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Rename & Budget Modals
  const [renameModal, setRenameModal] = useState<{ isOpen: boolean; campaignId: string; name: string }>({
    isOpen: false, campaignId: '', name: ''
  });
  const [budgetModal, setBudgetModal] = useState<{ isOpen: boolean; campaignId: string; budget: number }>({
    isOpen: false, campaignId: '', budget: 100
  });

  // Audit Log Drawer State
  const [isAuditLogsOpen, setIsAuditLogsOpen] = useState<boolean>(false);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);

  // Fetch campaigns from server when filters change
  const loadCampaigns = async () => {
    setLoading(true);
    try {
      const res = await getCampaigns({
        search: searchTerm,
        status: statusFilter,
        objective: objectiveFilter,
        sort_by: sortBy,
        sort_order: sortOrder,
        limit,
        offset: (page - 1) * limit
      });
      if (Array.isArray(res) && res.length > 0) {
        setCampaigns(res);
      } else if (initialCampaigns.length > 0 && !searchTerm && statusFilter === 'ALL') {
        setCampaigns(initialCampaigns);
      } else {
        setCampaigns([]);
      }
    } catch (err) {
      console.error('Failed to fetch campaigns:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCampaigns();
  }, [searchTerm, statusFilter, objectiveFilter, sortBy, sortOrder, page]);

  // Load Audit Logs
  const loadAuditLogs = async (campaignId?: string) => {
    try {
      const logs = await fetchCampaignAuditLogs(campaignId);
      if (Array.isArray(logs)) {
        setAuditLogs(logs);
      }
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    }
  };

  const showToast = (type: 'success' | 'error', text: string) => {
    setToastMessage({ type, text });
    setTimeout(() => setToastMessage(null), 4000);
  };

  // Selection Logic
  const handleSelectAll = () => {
    if (selectedCampaignIds.length === campaigns.length) {
      setSelectedCampaignIds([]);
    } else {
      setSelectedCampaignIds(campaigns.map(c => c.campaign_id || c.id));
    }
  };

  const handleSelectOne = (id: string) => {
    if (selectedCampaignIds.includes(id)) {
      setSelectedCampaignIds(selectedCampaignIds.filter(i => i !== id));
    } else {
      setSelectedCampaignIds([...selectedCampaignIds, id]);
    }
  };

  // Single Action Optimistic Handlers with Rollback
  const executePause = async (campaignId: string) => {
    const backup = [...campaigns];
    setCampaigns(prev => prev.map(c => (c.campaign_id === campaignId || c.id === campaignId) ? { ...c, status: 'PAUSED' } : c));
    try {
      await pauseCampaign(campaignId);
      showToast('success', 'Campaign paused successfully.');
    } catch (err) {
      setCampaigns(backup);
      showToast('error', 'Failed to pause campaign. Changes rolled back.');
    }
  };

  const executeResume = async (campaignId: string) => {
    const backup = [...campaigns];
    setCampaigns(prev => prev.map(c => (c.campaign_id === campaignId || c.id === campaignId) ? { ...c, status: 'ACTIVE' } : c));
    try {
      await resumeCampaign(campaignId);
      showToast('success', 'Campaign resumed successfully.');
    } catch (err) {
      setCampaigns(backup);
      showToast('error', 'Failed to resume campaign. Changes rolled back.');
    }
  };

  const executeArchive = async (campaignId: string) => {
    const backup = [...campaigns];
    setCampaigns(prev => prev.map(c => (c.campaign_id === campaignId || c.id === campaignId) ? { ...c, status: 'ARCHIVED' } : c));
    try {
      await archiveCampaign(campaignId);
      showToast('success', 'Campaign archived successfully.');
    } catch (err) {
      setCampaigns(backup);
      showToast('error', 'Failed to archive campaign. Changes rolled back.');
    }
  };

  const executeDuplicate = async (campaignId: string) => {
    try {
      const newCamp: any = await duplicateCampaign(campaignId);
      if (newCamp && newCamp.campaign_id) {
        setCampaigns([newCamp, ...campaigns]);
        showToast('success', 'Campaign duplicated successfully.');
      }
    } catch (err) {
      showToast('error', 'Failed to duplicate campaign.');
    }
  };

  const executeRename = async (campaignId: string, newName: string) => {
    const backup = [...campaigns];
    setCampaigns(prev => prev.map(c => (c.campaign_id === campaignId || c.id === campaignId) ? { ...c, name: newName } : c));
    try {
      await renameCampaign(campaignId, newName);
      showToast('success', 'Campaign renamed successfully.');
    } catch (err) {
      setCampaigns(backup);
      showToast('error', 'Failed to rename campaign. Changes rolled back.');
    }
  };

  const executeBudgetEdit = async (campaignId: string, newBudget: number) => {
    const backup = [...campaigns];
    setCampaigns(prev => prev.map(c => (c.campaign_id === campaignId || c.id === campaignId) ? { ...c, daily_budget: newBudget } : c));
    try {
      await editCampaignBudget(campaignId, newBudget);
      showToast('success', 'Daily budget updated successfully.');
    } catch (err) {
      setCampaigns(backup);
      showToast('error', 'Failed to update budget. Changes rolled back.');
    }
  };

  const executeBudgetAdjustment = async (campaignId: string, action: 'increase' | 'decrease', pct: number) => {
    const backup = [...campaigns];
    setCampaigns(prev => prev.map(c => {
      if (c.campaign_id === campaignId || c.id === campaignId) {
        const current = c.daily_budget || 100;
        const updated = action === 'increase' ? current * (1 + pct / 100) : Math.max(1, current * (1 - pct / 100));
        return { ...c, daily_budget: Math.round(updated * 100) / 100 };
      }
      return c;
    }));
    try {
      if (action === 'increase') await increaseCampaignBudget(campaignId, pct);
      else await decreaseCampaignBudget(campaignId, pct);
      showToast('success', `Budget ${action}d by ${pct}% successfully.`);
    } catch (err) {
      setCampaigns(backup);
      showToast('error', `Failed to ${action} budget. Changes rolled back.`);
    }
  };

  // Bulk Action Optimistic Handler
  const executeBulkAction = async (action: string, payload?: any) => {
    if (selectedCampaignIds.length === 0) return;
    const backup = [...campaigns];
    
    // Optimistic update
    setCampaigns(prev => prev.map(c => {
      const cid = c.campaign_id || c.id;
      if (selectedCampaignIds.includes(cid)) {
        if (action === 'pause') return { ...c, status: 'PAUSED' };
        if (action === 'resume') return { ...c, status: 'ACTIVE' };
        if (action === 'archive') return { ...c, status: 'ARCHIVED' };
        if (action === 'increase_budget') return { ...c, daily_budget: Math.round(((c.daily_budget || 100) * 1.2) * 100) / 100 };
        if (action === 'decrease_budget') return { ...c, daily_budget: Math.round(Math.max(1, (c.daily_budget || 100) * 0.9) * 100) / 100 };
        if (action === 'update_budget' && payload?.daily_budget) return { ...c, daily_budget: payload.daily_budget };
      }
      return c;
    }));

    try {
      await bulkCampaignAction({
        campaign_ids: selectedCampaignIds,
        action,
        daily_budget: payload?.daily_budget,
        percentage: payload?.percentage
      });
      showToast('success', `Bulk action '${action}' applied to ${selectedCampaignIds.length} campaigns.`);
      setSelectedCampaignIds([]);
    } catch (err) {
      setCampaigns(backup);
      showToast('error', `Failed to execute bulk action '${action}'. Changes rolled back.`);
    }
  };

  // Handle Confirmed Modal Action
  const handleConfirmAction = async () => {
    setActionLoading(true);
    const { actionType, targetId, payload } = confirmModal;
    setConfirmModal(prev => ({ ...prev, isOpen: false }));

    if (actionType === 'pause' && targetId) await executePause(targetId);
    else if (actionType === 'resume' && targetId) await executeResume(targetId);
    else if (actionType === 'archive' && targetId) await executeArchive(targetId);
    else if (actionType === 'duplicate' && targetId) await executeDuplicate(targetId);
    else if (actionType === 'rename' && targetId && payload?.name) await executeRename(targetId, payload.name);
    else if (actionType === 'budget_edit' && targetId && payload?.budget) await executeBudgetEdit(targetId, payload.budget);
    else if (actionType === 'budget_increase' && targetId) await executeBudgetAdjustment(targetId, 'increase', payload?.pct || 20);
    else if (actionType === 'budget_decrease' && targetId) await executeBudgetAdjustment(targetId, 'decrease', payload?.pct || 10);
    else if (actionType.startsWith('bulk_')) await executeBulkAction(actionType.replace('bulk_', ''), payload);

    setActionLoading(false);
  };

  return (
    <div className="space-y-6">
      {/* Toast Alert Banner */}
      <AnimatePresence>
        {toastMessage && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className={`p-4 rounded-2xl flex items-center justify-between shadow-lg border text-sm font-semibold ${
              toastMessage.type === 'success'
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
                : 'bg-rose-500/10 border-rose-500/30 text-rose-600 dark:text-rose-400'
            }`}
          >
            <div className="flex items-center gap-2">
              {toastMessage.type === 'success' ? <Check className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
              <span>{toastMessage.text}</span>
            </div>
            <button onClick={() => setToastMessage(null)} className="p-1 hover:bg-black/5 rounded-lg">
              <X className="w-4 h-4" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header Controls & Filter Bar */}
      <div className="p-5 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-black text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <ShieldCheck className="w-6 h-6 text-indigo-500" />
              Meta Campaign Management Console
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Manage synced Meta ad campaigns, adjust budgets, and audit real-time changes
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                loadAuditLogs();
                setIsAuditLogsOpen(true);
              }}
              className="px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-2 transition cursor-pointer"
            >
              <History className="w-4 h-4 text-indigo-500" />
              Audit Logs
            </button>

            <button
              onClick={loadCampaigns}
              className="p-2 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition cursor-pointer"
              title="Refresh Campaigns"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Filters and Search Bar */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 pt-2">
          {/* Search Box */}
          <div className="relative md:col-span-1">
            <Search className="w-4 h-4 absolute left-3.5 top-3 text-slate-400" />
            <input
              type="text"
              placeholder="Search campaign name or ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/80 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* Status Filter */}
          <div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/80 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="ALL">Status: All</option>
              <option value="ACTIVE">ACTIVE</option>
              <option value="PAUSED">PAUSED</option>
              <option value="ARCHIVED">ARCHIVED</option>
            </select>
          </div>

          {/* Objective Filter */}
          <div>
            <select
              value={objectiveFilter}
              onChange={(e) => setObjectiveFilter(e.target.value)}
              className="w-full px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/80 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="ALL">Objective: All</option>
              <option value="OUTCOME_SALES">Sales / Conversions</option>
              <option value="OUTCOME_LEADS">Lead Generation</option>
              <option value="OUTCOME_TRAFFIC">Traffic</option>
              <option value="OUTCOME_AWARENESS">Awareness</option>
              <option value="OUTCOME_ENGAGEMENT">Engagement</option>
            </select>
          </div>

          {/* Sorting Control */}
          <div>
            <select
              value={`${sortBy}_${sortOrder}`}
              onChange={(e) => {
                const parts = e.target.value.split('_');
                setSortOrder(parts.pop() as 'asc' | 'desc');
                setSortBy(parts.join('_'));
              }}
              className="w-full px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/80 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="created_at_desc">Sort: Newest First</option>
              <option value="created_at_asc">Sort: Oldest First</option>
              <option value="spend_desc">Sort: Highest Spend</option>
              <option value="revenue_desc">Sort: Highest Revenue</option>
              <option value="roas_desc">Sort: Highest ROAS</option>
              <option value="cpa_asc">Sort: Lowest CPA</option>
              <option value="name_asc">Sort: Campaign Name (A-Z)</option>
            </select>
          </div>
        </div>

        {/* Multi-Select Bulk Actions Bar */}
        {selectedCampaignIds.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="p-3 bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800/50 rounded-2xl flex flex-wrap items-center justify-between gap-3 text-xs"
          >
            <div className="font-bold text-indigo-700 dark:text-indigo-300">
              {selectedCampaignIds.length} campaign{selectedCampaignIds.length > 1 ? 's' : ''} selected
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => setConfirmModal({
                  isOpen: true,
                  title: 'Bulk Pause Campaigns',
                  description: `Are you sure you want to pause ${selectedCampaignIds.length} selected campaigns?`,
                  actionType: 'bulk_pause'
                })}
                className="px-3 py-1.5 rounded-xl bg-amber-500 text-white font-bold hover:bg-amber-600 transition cursor-pointer flex items-center gap-1"
              >
                <Pause className="w-3.5 h-3.5" /> Pause All
              </button>

              <button
                onClick={() => setConfirmModal({
                  isOpen: true,
                  title: 'Bulk Resume Campaigns',
                  description: `Are you sure you want to activate ${selectedCampaignIds.length} selected campaigns?`,
                  actionType: 'bulk_resume'
                })}
                className="px-3 py-1.5 rounded-xl bg-emerald-600 text-white font-bold hover:bg-emerald-700 transition cursor-pointer flex items-center gap-1"
              >
                <Play className="w-3.5 h-3.5" /> Resume All
              </button>

              <button
                onClick={() => setConfirmModal({
                  isOpen: true,
                  title: 'Bulk Increase Budget (+20%)',
                  description: `Increase daily budget by 20% for ${selectedCampaignIds.length} selected campaigns?`,
                  actionType: 'bulk_increase_budget',
                  payload: { percentage: 20 }
                })}
                className="px-3 py-1.5 rounded-xl bg-indigo-600 text-white font-bold hover:bg-indigo-700 transition cursor-pointer flex items-center gap-1"
              >
                <TrendingUp className="w-3.5 h-3.5" /> +20% Budget
              </button>

              <button
                onClick={() => setConfirmModal({
                  isOpen: true,
                  title: 'Bulk Archive Campaigns',
                  description: `Archive ${selectedCampaignIds.length} selected campaigns? This will stop ad delivery.`,
                  actionType: 'bulk_archive',
                  isDangerous: true
                })}
                className="px-3 py-1.5 rounded-xl bg-slate-700 text-white font-bold hover:bg-slate-800 transition cursor-pointer flex items-center gap-1"
              >
                <Archive className="w-3.5 h-3.5" /> Archive All
              </button>
            </div>
          </motion.div>
        )}
      </div>

      {/* Main Campaign Table */}
      <div className="p-5 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-extrabold uppercase text-slate-400 tracking-wider">
                <th className="py-3 px-3 w-10">
                  <button onClick={handleSelectAll} className="cursor-pointer">
                    {selectedCampaignIds.length === campaigns.length && campaigns.length > 0 ? (
                      <CheckSquare className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                    ) : (
                      <Square className="w-4 h-4 text-slate-400" />
                    )}
                  </button>
                </th>
                <th className="py-3 px-3">Campaign</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-3 text-right">Daily Budget</th>
                <th className="py-3 px-3 text-right">Spend</th>
                <th className="py-3 px-3 text-right">Revenue</th>
                <th className="py-3 px-3 text-right">ROAS</th>
                <th className="py-3 px-3 text-right">CPA</th>
                <th className="py-3 px-3 text-right">CTR</th>
                <th className="py-3 px-3 text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-xs font-semibold">
              {loading ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-slate-400">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-500" />
                    Loading campaign engine telemetry...
                  </td>
                </tr>
              ) : campaigns.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-slate-400">
                    No active campaigns match your criteria. Try adjusting your search filters.
                  </td>
                </tr>
              ) : (
                campaigns.map((c) => {
                  const cid = c.campaign_id || c.id;
                  const isSelected = selectedCampaignIds.includes(cid);
                  return (
                    <tr
                      key={cid}
                      className={`hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition ${
                        isSelected ? 'bg-indigo-50/40 dark:bg-indigo-950/20' : ''
                      }`}
                    >
                      <td className="py-3 px-3">
                        <button onClick={() => handleSelectOne(cid)} className="cursor-pointer">
                          {isSelected ? (
                            <CheckSquare className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                          ) : (
                            <Square className="w-4 h-4 text-slate-300 dark:text-slate-600" />
                          )}
                        </button>
                      </td>

                      <td className="py-3 px-3">
                        <div className="font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                          <span>{c.name}</span>
                          <button
                            onClick={() => setRenameModal({ isOpen: true, campaignId: cid, name: c.name })}
                            className="p-1 hover:text-indigo-600 text-slate-400 cursor-pointer"
                            title="Rename Campaign"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono">ID: {cid}</div>
                      </td>

                      <td className="py-3 px-3">
                        <span
                          className={`px-2 py-0.5 rounded-md text-[10px] font-extrabold border ${
                            c.status === 'ACTIVE'
                              ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
                              : c.status === 'PAUSED'
                              ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20'
                              : 'bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20'
                          }`}
                        >
                          {c.status}
                        </span>
                      </td>

                      <td className="py-3 px-3 text-right">
                        <div className="font-bold text-slate-800 dark:text-slate-200 flex items-center justify-end gap-1">
                          ${(c.daily_budget || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                          <button
                            onClick={() => setBudgetModal({ isOpen: true, campaignId: cid, budget: c.daily_budget || 100 })}
                            className="p-1 hover:text-indigo-600 text-slate-400 cursor-pointer"
                            title="Edit Budget"
                          >
                            <DollarSign className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>

                      <td className="py-3 px-3 text-right font-medium">
                        ${(c.spend || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                      </td>

                      <td className="py-3 px-3 text-right font-semibold text-emerald-600 dark:text-emerald-400">
                        ${(c.revenue || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                      </td>

                      <td className="py-3 px-3 text-right font-bold text-indigo-600 dark:text-indigo-400">
                        {(c.roas || 0).toFixed(2)}x
                      </td>

                      <td className="py-3 px-3 text-right font-medium">
                        ${(c.cpa || 0).toFixed(2)}
                      </td>

                      <td className="py-3 px-3 text-right font-medium">
                        {(c.ctr || 0).toFixed(2)}%
                      </td>

                      <td className="py-3 px-3 text-center">
                        <div className="flex items-center justify-center gap-1">
                          {c.status === 'ACTIVE' ? (
                            <button
                              onClick={() => setConfirmModal({
                                isOpen: true,
                                title: 'Pause Campaign',
                                description: `Are you sure you want to pause "${c.name}"?`,
                                actionType: 'pause',
                                targetId: cid
                              })}
                              className="p-1.5 rounded-lg bg-amber-50 dark:bg-amber-950/40 text-amber-600 hover:bg-amber-100 transition cursor-pointer"
                              title="Pause Campaign"
                            >
                              <Pause className="w-3.5 h-3.5" />
                            </button>
                          ) : (
                            <button
                              onClick={() => setConfirmModal({
                                isOpen: true,
                                title: 'Resume Campaign',
                                description: `Activate "${c.name}" on Meta Graph API?`,
                                actionType: 'resume',
                                targetId: cid
                              })}
                              className="p-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 hover:bg-emerald-100 transition cursor-pointer"
                              title="Resume Campaign"
                            >
                              <Play className="w-3.5 h-3.5" />
                            </button>
                          )}

                          <button
                            onClick={() => setConfirmModal({
                              isOpen: true,
                              title: 'Duplicate Campaign',
                              description: `Create a copy of "${c.name}"?`,
                              actionType: 'duplicate',
                              targetId: cid
                            })}
                            className="p-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 transition cursor-pointer"
                            title="Duplicate Campaign"
                          >
                            <Copy className="w-3.5 h-3.5" />
                          </button>

                          <button
                            onClick={() => setConfirmModal({
                              isOpen: true,
                              title: 'Increase Budget (+20%)',
                              description: `Scale budget for "${c.name}" by +20%?`,
                              actionType: 'budget_increase',
                              targetId: cid,
                              payload: { pct: 20 }
                            })}
                            className="p-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 hover:bg-indigo-100 transition cursor-pointer"
                            title="Increase Budget +20%"
                          >
                            <TrendingUp className="w-3.5 h-3.5" />
                          </button>

                          <button
                            onClick={() => setConfirmModal({
                              isOpen: true,
                              title: 'Archive Campaign',
                              description: `Archive "${c.name}"? Delivery will halt immediately.`,
                              actionType: 'archive',
                              targetId: cid,
                              isDangerous: true
                            })}
                            className="p-1.5 rounded-lg bg-rose-50 dark:bg-rose-950/40 text-rose-600 hover:bg-rose-100 transition cursor-pointer"
                            title="Archive Campaign"
                          >
                            <Archive className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Controls */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-100 dark:border-slate-800 text-xs">
          <div className="text-slate-500">
            Showing Page <span className="font-bold text-slate-900 dark:text-slate-100">{page}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
              className="px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 disabled:opacity-40 font-semibold cursor-pointer"
            >
              <ChevronLeft className="w-4 h-4 inline" /> Prev
            </button>
            <button
              disabled={campaigns.length < limit}
              onClick={() => setPage(page + 1)}
              className="px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 disabled:opacity-40 font-semibold cursor-pointer"
            >
              Next <ChevronRight className="w-4 h-4 inline" />
            </button>
          </div>
        </div>
      </div>

      {/* Action Confirmation Modal */}
      <AnimatePresence>
        {confirmModal.isOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-xs">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 rounded-3xl max-w-md w-full shadow-2xl space-y-4"
            >
              <div className="flex items-center gap-3">
                <div className={`p-3 rounded-2xl ${confirmModal.isDangerous ? 'bg-rose-500/10 text-rose-500' : 'bg-indigo-500/10 text-indigo-500'}`}>
                  <AlertTriangle className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">{confirmModal.title}</h3>
                  <p className="text-xs text-slate-500">{confirmModal.description}</p>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  onClick={() => setConfirmModal(prev => ({ ...prev, isOpen: false }))}
                  className="px-4 py-2 rounded-xl text-xs font-bold border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmAction}
                  disabled={actionLoading}
                  className={`px-4 py-2 rounded-xl text-xs font-bold text-white transition cursor-pointer flex items-center gap-2 ${
                    confirmModal.isDangerous ? 'bg-rose-600 hover:bg-rose-700' : 'bg-indigo-600 hover:bg-indigo-700'
                  }`}
                >
                  {actionLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  Confirm Action
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Rename Modal */}
      <AnimatePresence>
        {renameModal.isOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-xs">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 rounded-3xl max-w-md w-full shadow-2xl space-y-4"
            >
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">Rename Meta Campaign</h3>
              <div>
                <label className="text-xs font-semibold text-slate-500">New Campaign Name</label>
                <input
                  type="text"
                  value={renameModal.name}
                  onChange={(e) => setRenameModal(prev => ({ ...prev, name: e.target.value }))}
                  className="w-full mt-1 px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  onClick={() => setRenameModal(prev => ({ ...prev, isOpen: false }))}
                  className="px-4 py-2 rounded-xl text-xs font-bold border border-slate-200 dark:border-slate-700 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    const { campaignId, name } = renameModal;
                    setRenameModal(prev => ({ ...prev, isOpen: false }));
                    setConfirmModal({
                      isOpen: true,
                      title: 'Confirm Rename',
                      description: `Rename campaign to "${name}"?`,
                      actionType: 'rename',
                      targetId: campaignId,
                      payload: { name }
                    });
                  }}
                  className="px-4 py-2 rounded-xl text-xs font-bold bg-indigo-600 text-white cursor-pointer"
                >
                  Save Name
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Budget Modal */}
      <AnimatePresence>
        {budgetModal.isOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-xs">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 rounded-3xl max-w-md w-full shadow-2xl space-y-4"
            >
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">Set Daily Budget</h3>
              <div>
                <label className="text-xs font-semibold text-slate-500">Daily Budget (USD)</label>
                <input
                  type="number"
                  value={budgetModal.budget}
                  onChange={(e) => setBudgetModal(prev => ({ ...prev, budget: parseFloat(e.target.value) || 0 }))}
                  className="w-full mt-1 px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs font-medium focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  onClick={() => setBudgetModal(prev => ({ ...prev, isOpen: false }))}
                  className="px-4 py-2 rounded-xl text-xs font-bold border border-slate-200 dark:border-slate-700 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    const { campaignId, budget } = budgetModal;
                    setBudgetModal(prev => ({ ...prev, isOpen: false }));
                    setConfirmModal({
                      isOpen: true,
                      title: 'Confirm Budget Update',
                      description: `Set daily budget to $${budget}?`,
                      actionType: 'budget_edit',
                      targetId: campaignId,
                      payload: { budget }
                    });
                  }}
                  className="px-4 py-2 rounded-xl text-xs font-bold bg-indigo-600 text-white cursor-pointer"
                >
                  Update Budget
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Audit Logs Drawer */}
      <AnimatePresence>
        {isAuditLogsOpen && (
          <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/60 backdrop-blur-xs">
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              className="w-full max-w-xl bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 p-6 h-full overflow-y-auto space-y-4 shadow-2xl"
            >
              <div className="flex items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-800">
                <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <History className="w-5 h-5 text-indigo-500" />
                  Campaign Audit Logs
                </h2>
                <button onClick={() => setIsAuditLogsOpen(false)} className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg cursor-pointer">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-3">
                {auditLogs.length === 0 ? (
                  <p className="text-xs text-slate-400 py-8 text-center">No recent campaign audit records found.</p>
                ) : (
                  auditLogs.map((log) => (
                    <div key={log.id} className="p-3 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 space-y-1 text-xs">
                      <div className="flex items-center justify-between font-bold">
                        <span className="uppercase text-indigo-600 dark:text-indigo-400">{log.action}</span>
                        <span className="text-[10px] text-slate-400">{new Date(log.created_at).toLocaleString()}</span>
                      </div>
                      <div className="text-slate-700 dark:text-slate-300">
                        Campaign: <span className="font-mono">{log.campaign_id || 'N/A'}</span>
                      </div>
                      {log.old_value && <div className="text-slate-400 text-[11px]">Old: {log.old_value}</div>}
                      {log.new_value && <div className="text-emerald-500 text-[11px]">New: {log.new_value}</div>}
                    </div>
                  ))
                )}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default CampaignsView;
