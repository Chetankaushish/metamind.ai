import React from 'react';
import { motion } from 'motion/react';
import {
  LayoutDashboard,
  Layers,
  Sparkles,
  Zap,
  FileText,
  CreditCard,
  Building2,
  Settings,
  ChevronRight,
  Lock
} from 'lucide-react';
import { SaaSUser } from '../../types';
import { MetaMindLogo } from './MetaMindLogo';

export type NavTab =
  | 'dashboard'
  | 'campaigns'
  | 'copilot'
  | 'automations'
  | 'reports'
  | 'billing'
  | 'organizations'
  | 'settings'
  | 'adsets'
  | 'ads'
  | 'creatives'
  | 'audiences'
  | 'agency'
  | 'whitelabel'
  | 'security'
  | 'agents';

interface SidebarProps {
  activeTab: NavTab;
  setActiveTab: (tab: NavTab) => void;
  collapsed: boolean;
  setCollapsed: (val: boolean) => void;
  alertCount?: number;
  isMetaConnected?: boolean;
  user?: SaaSUser;
  onOpenFacebookOAuthModal?: () => void;
  onOpenAuthModal?: () => void;
  onOpenSessionModal?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  collapsed,
  setCollapsed,
  alertCount = 0,
  isMetaConnected = false,
  user,
  onOpenFacebookOAuthModal,
  onOpenAuthModal,
  onOpenSessionModal
}) => {
  const navItems = [
    { id: 'dashboard' as NavTab, label: 'Dashboard', icon: LayoutDashboard },
    { id: 'campaigns' as NavTab, label: 'Campaigns', icon: Layers, requiresMeta: true },
    { id: 'copilot' as NavTab, label: 'AI Copilot', icon: Sparkles, live: true, requiresMeta: true },
    { id: 'automations' as NavTab, label: 'Automation', icon: Zap, alert: alertCount > 0, requiresMeta: true },
    { id: 'reports' as NavTab, label: 'Reports', icon: FileText, requiresMeta: true },
    { id: 'billing' as NavTab, label: 'Billing', icon: CreditCard },
    { id: 'organizations' as NavTab, label: 'Organizations', icon: Building2 },
    { id: 'settings' as NavTab, label: 'Settings', icon: Settings }
  ];

  return (
    <aside
      className={`fixed left-0 top-0 bottom-0 z-30 border-r border-slate-200/80 dark:border-slate-800/80 bg-white/95 dark:bg-slate-950/95 backdrop-blur-xl transition-all duration-300 ease-in-out flex flex-col justify-between ${
        collapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Sidebar Header: Logo & App Name at Very Top */}
      <div className="h-20 px-3.5 flex items-center border-b border-slate-200/80 dark:border-slate-800/80 shrink-0">
        {collapsed ? (
          <div className="w-full flex items-center justify-center">
            <motion.div
              whileHover={{ scale: 1.05, rotate: 2 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setCollapsed(false)}
              className="cursor-pointer"
              title="Expand Sidebar"
            >
              <MetaMindLogo size={36} className="w-9 h-9" />
            </motion.div>
          </div>
        ) : (
          <div className="flex items-center gap-3 w-full">
            <motion.div
              whileHover={{ scale: 1.05, rotate: 2 }}
              whileTap={{ scale: 0.95 }}
              className="cursor-pointer shrink-0"
            >
              <MetaMindLogo size={40} className="w-10 h-10" />
            </motion.div>

            <div className="flex flex-col min-w-0 flex-1 justify-center">
              <span className="font-extrabold tracking-tight text-[15px] bg-gradient-to-r from-slate-900 via-indigo-950 to-purple-900 dark:from-white dark:via-indigo-100 dark:to-purple-200 bg-clip-text text-transparent truncate leading-tight">
                MetaMind AI
              </span>
              <span className="text-[9.5px] font-medium tracking-[0.18em] uppercase text-slate-500 dark:text-purple-300/80 truncate leading-none mt-1">
                By Volzad
              </span>
            </div>
          </div>
        )}
      </div>

      <div className="flex-1 px-2.5 py-3 space-y-1 overflow-y-auto custom-scrollbar">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isLocked = !isMetaConnected && item.requiresMeta;
          const isActive =
            activeTab === item.id ||
            (item.id === 'campaigns' && ['adsets', 'ads', 'creatives', 'audiences'].includes(activeTab)) ||
            (item.id === 'organizations' && activeTab === 'agency') ||
            (item.id === 'settings' && ['whitelabel', 'security'].includes(activeTab));

          const handleClick = () => {
            if (isLocked) {
              if (onOpenFacebookOAuthModal) {
                onOpenFacebookOAuthModal();
              } else {
                setActiveTab('dashboard');
              }
              return;
            }
            setActiveTab(item.id);
          };

          const tooltipText = isLocked
            ? 'Connect your Meta Business Account to unlock this feature.'
            : collapsed
            ? item.label
            : undefined;

          return (
            <button
              key={item.id}
              onClick={handleClick}
              className={`w-full relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all duration-200 group ${
                isLocked
                  ? 'text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100/60 dark:hover:bg-slate-800/40 cursor-pointer'
                  : isActive
                  ? 'text-white font-semibold'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100/80 dark:hover:bg-slate-800/60'
              }`}
              title={tooltipText}
            >
              {!isLocked && isActive && (
                <motion.div
                  layoutId="activeSidebarTab"
                  className="absolute inset-0 bg-gradient-to-r from-indigo-600 via-indigo-600 to-purple-600 rounded-xl shadow-md shadow-indigo-500/25 z-0"
                  transition={{ type: 'spring', bounce: 0.15, duration: 0.35 }}
                />
              )}

              <span className="relative z-10 flex items-center justify-center w-5 h-5 shrink-0">
                <Icon
                  className={`w-4.5 h-4.5 shrink-0 transition-all duration-200 ${
                    isLocked
                      ? 'text-slate-400 dark:text-slate-500'
                      : isActive
                      ? 'text-white scale-110'
                      : 'text-slate-400 group-hover:scale-110 group-hover:text-slate-700 dark:group-hover:text-slate-200'
                  }`}
                />
              </span>

              {!collapsed && (
                <div className="relative z-10 flex-1 flex items-center justify-between text-left truncate">
                  <span className={`truncate ${isLocked ? 'text-slate-400 dark:text-slate-500' : ''}`}>
                    {item.label}
                  </span>

                  {isLocked ? (
                    <span title="Connect your Meta Business Account to unlock this feature.">
                      <Lock
                      className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500 shrink-0 ml-1"
                      />
                      </span>
                  ) : (
                    <>
                      {item.live && !isActive && (
                        <span className="flex h-2 w-2 relative">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
                        </span>
                      )}

                      {item.alert && !isActive && (
                        <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                      )}
                    </>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </div>

      <div className="p-2.5 border-t border-slate-200/80 dark:border-slate-800/80 space-y-2 bg-slate-50/50 dark:bg-slate-900/30 shrink-0">
        {!collapsed ? (
          <div className="p-2.5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800/80 shadow-2xs space-y-2">
            {user && (
              <div
                onClick={() => onOpenAuthModal && onOpenAuthModal()}
                className="flex items-center gap-2.5 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50 p-1 rounded-xl transition"
                title="Account Settings & Authentication"
              >
                <div className="relative shrink-0">
                  <img
                    src={user.avatarUrl}
                    alt={user.fullName}
                    className="w-8 h-8 rounded-full object-cover ring-2 ring-indigo-500/20"
                  />
                  <span
                    className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full ring-2 ring-white dark:ring-slate-900 ${
                      isMetaConnected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'
                    }`}
                    title={isMetaConnected ? 'Meta API Online' : 'Meta API Disconnected'}
                  />
                </div>
                <div className="flex flex-col min-w-0 flex-1">
                  <span className="text-xs font-bold text-slate-900 dark:text-slate-100 truncate">
                    {user.fullName}
                  </span>
                  <span className="text-[10px] text-slate-500 dark:text-slate-400 truncate flex items-center gap-1">
                    {user.role} • <span className="text-indigo-600 dark:text-indigo-400 font-semibold">{user.plan}</span>
                  </span>
                </div>
              </div>
            )}

            <div className="pt-2 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-[10px]">
              <button
                onClick={() => onOpenSessionModal && onOpenSessionModal()}
                className="font-semibold text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1"
              >
                <Lock className="w-3 h-3" />
                <span>Active Sessions</span>
              </button>
              <button
                onClick={() => onOpenAuthModal && onOpenAuthModal()}
                className="text-slate-500 dark:text-slate-400 hover:text-slate-900 font-medium"
              >
                Sign In / Switch
              </button>
            </div>
          </div>
        ) : (
          user && (
            <div className="flex justify-center my-1">
              <div className="relative shrink-0" title={`${user.fullName} (${isMetaConnected ? 'Meta Connected' : 'Meta Disconnected'})`}>
                <img
                  src={user.avatarUrl}
                  alt={user.fullName}
                  className="w-8 h-8 rounded-full object-cover ring-2 ring-indigo-500/20"
                />
                <span
                  className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full ring-2 ring-white dark:ring-slate-900 ${
                    isMetaConnected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'
                  }`}
                />
              </div>
            </div>
          )
        )}

        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center p-2 rounded-xl text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/80 transition-colors duration-200"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          <ChevronRight className={`w-4 h-4 transition-transform duration-300 ${collapsed ? '' : 'rotate-180'}`} />
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
