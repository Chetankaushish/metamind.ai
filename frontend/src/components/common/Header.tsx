import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Bell,
  Sun,
  Moon,
  Monitor,
  ChevronDown,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Building2,
  ShieldCheck,
  Sparkles,
  Search,
  Facebook,
  Command,
  Key
} from 'lucide-react';
import { MetaBusinessManager, MetaAdAccount, SaaSUser, MetaTokenInfo } from '../../types';
import { useTheme } from '../../contexts/ThemeContext';

const defaultUser: SaaSUser = {
  fullName: 'Admin User',
  email: 'admin@system.local',
  role: 'Admin',
  avatarUrl: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
  companyName: 'No organization configured',
  plan: 'Billing not configured'
};

export type HeaderPopupType = 'bm' | 'acc' | 'notifications' | 'user' | 'theme' | null;

interface HeaderProps {
  darkMode?: boolean;
  setDarkMode?: React.Dispatch<React.SetStateAction<boolean>> | ((val: boolean | ((prev: boolean) => boolean)) => void);
  theme?: 'dark' | 'light';
  toggleTheme?: () => void;
  isSyncing?: boolean;
  onManualSync?: () => void;
  user?: SaaSUser;
  onOpenCopilot?: () => void;
  onOpenCommandPalette?: () => void;
  activePlatformTab?: string;
  setActivePlatformTab?: (tab: string) => void;
  activeTab?: string;
  notifications?: any[];
  setNotifications?: React.Dispatch<React.SetStateAction<any[]>>;
  isMetaConnected: boolean;
  setIsMetaConnected: (val: boolean) => void;
  businessManagers: MetaBusinessManager[];
  selectedBm: MetaBusinessManager;
  setSelectedBm: (bm: MetaBusinessManager) => void;
  adAccounts: MetaAdAccount[];
  selectedAccount: MetaAdAccount;
  setSelectedAccount: (acc: MetaAdAccount) => void;
  tokenInfo?: MetaTokenInfo;
  onOpenFacebookOAuthModal: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  darkMode,
  setDarkMode,
  theme,
  toggleTheme,
  isSyncing = false,
  onManualSync,
  user,
  onOpenCopilot,
  onOpenCommandPalette,
  activePlatformTab = 'overview',
  activeTab,
  notifications = [],
  isMetaConnected,
  setIsMetaConnected,
  businessManagers,
  selectedBm,
  setSelectedBm,
  adAccounts,
  selectedAccount,
  setSelectedAccount,
  tokenInfo,
  onOpenFacebookOAuthModal
}) => {
  const [activePopup, setActivePopup] = useState<HeaderPopupType>(null);
  const { theme: currentTheme, resolvedTheme, setTheme: setSystemTheme, toggleTheme: toggleSystemTheme } = useTheme();

  const headerRef = useRef<HTMLElement>(null);
  const bmTriggerRef = useRef<HTMLButtonElement>(null);
  const accTriggerRef = useRef<HTMLButtonElement>(null);
  const notificationsTriggerRef = useRef<HTMLButtonElement>(null);
  const userTriggerRef = useRef<HTMLButtonElement>(null);
  const themeTriggerRef = useRef<HTMLButtonElement>(null);

  const currentUser = user || defaultUser;
  const isDark = resolvedTheme === 'dark';

  const handleToggleTheme = () => {
    toggleSystemTheme();
    if (toggleTheme) toggleTheme();
    if (setDarkMode) setDarkMode(resolvedTheme !== 'dark');
  };

  const togglePopup = (popup: HeaderPopupType) => {
    setActivePopup((prev) => (prev === popup ? null : popup));
  };

  useEffect(() => {
    setActivePopup(null);
  }, [activePlatformTab, activeTab]);

  useEffect(() => {
    if (!activePopup) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (headerRef.current && !headerRef.current.contains(e.target as Node)) {
        setActivePopup(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [activePopup]);

  return (
    <header
      ref={headerRef}
      className="sticky top-0 z-30 h-16 border-b border-slate-200/80 dark:border-slate-800/80 bg-white/90 dark:bg-slate-950/90 backdrop-blur-xl transition-colors duration-200 px-4 lg:px-6 flex items-center justify-between"
    >
      <div className="flex items-center gap-2 sm:gap-2.5 shrink-0">
        {isMetaConnected && (
          <>
            <div className="relative">
              <button
                ref={bmTriggerRef}
                id="header-bm-trigger"
                onClick={() => togglePopup('bm')}
                className={`h-9 flex items-center gap-2 px-3 rounded-xl border text-xs font-semibold transition ${
                  activePopup === 'bm'
                    ? 'bg-slate-200 dark:bg-slate-800 border-indigo-500/50 text-slate-900 dark:text-white'
                    : 'bg-slate-100/90 dark:bg-slate-900/90 border-slate-200/80 dark:border-slate-800 text-slate-700 dark:text-slate-200'
                }`}
              >
                <Building2 className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                <span className="max-w-[120px] sm:max-w-[150px] truncate">{selectedBm?.name || 'Select BM'}</span>
                <ChevronDown className={`w-3.5 h-3.5 text-slate-400 shrink-0 transition-transform ${activePopup === 'bm' ? 'rotate-180' : ''}`} />
              </button>

              <AnimatePresence>
                {activePopup === 'bm' && (
                  <motion.div
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 6 }}
                    className="absolute left-0 mt-2 w-64 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl p-2 text-xs z-50"
                  >
                    <p className="px-2.5 py-1 text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                      Meta Business Managers
                    </p>
                    <div className="space-y-1 mt-1">
                      {businessManagers.map((bm) => (
                        <button
                          key={bm.id}
                          onClick={() => {
                            setSelectedBm(bm);
                            setActivePopup(null);
                          }}
                          className={`w-full p-2 rounded-xl text-left flex items-center justify-between transition ${
                            selectedBm?.id === bm.id
                              ? 'bg-blue-50 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 font-semibold'
                              : 'hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300'
                          }`}
                        >
                          <span className="truncate">{bm.name}</span>
                          {selectedBm?.id === bm.id && <CheckCircle2 className="w-3.5 h-3.5 text-blue-500 shrink-0" />}
                        </button>
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <div className="relative">
              <button
                ref={accTriggerRef}
                onClick={() => togglePopup('acc')}
                className={`h-9 flex items-center gap-2 px-3 rounded-xl border text-xs font-semibold transition ${
                  activePopup === 'acc'
                    ? 'bg-blue-100 dark:bg-blue-900/80 border-blue-400 text-blue-800 dark:text-blue-200'
                    : 'bg-blue-50/90 dark:bg-blue-950/50 border-blue-200/80 dark:border-blue-900/80 text-blue-700 dark:text-blue-300'
                }`}
              >
                <Facebook className="w-3.5 h-3.5 text-blue-600 shrink-0 fill-current" />
                <span className="max-w-[120px] sm:max-w-[150px] truncate">{selectedAccount?.accountName || 'Ad Account'}</span>
                <ChevronDown className={`w-3.5 h-3.5 text-blue-400 shrink-0 transition-transform ${activePopup === 'acc' ? 'rotate-180' : ''}`} />
              </button>

              <AnimatePresence>
                {activePopup === 'acc' && (
                  <motion.div
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 6 }}
                    className="absolute left-0 mt-2 w-72 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl p-2 text-xs z-50"
                  >
                    <p className="px-2.5 py-1 text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                      Meta Ad Accounts
                    </p>
                    <div className="space-y-1 mt-1">
                      {adAccounts
                        .filter((acc) => !selectedBm || acc.businessManagerId === selectedBm.id)
                        .map((acc) => (
                          <button
                            key={acc.id}
                            onClick={() => {
                              setSelectedAccount(acc);
                              setActivePopup(null);
                            }}
                            className={`w-full p-2.5 rounded-xl text-left flex items-center justify-between transition ${
                              selectedAccount?.id === acc.id
                                ? 'bg-blue-600 text-white font-semibold'
                                : 'hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300'
                            }`}
                          >
                            <div className="truncate">
                              <p className="truncate">{acc.accountName}</p>
                              <p className={`text-[10px] ${selectedAccount?.id === acc.id ? 'text-blue-100' : 'text-slate-400'}`}>
                                {acc.accountId}
                              </p>
                            </div>
                            {selectedAccount?.id === acc.id && <CheckCircle2 className="w-4 h-4 text-white shrink-0 ml-1" />}
                          </button>
                        ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </>
        )}
      </div>

      <div className="flex-1 max-w-lg mx-3 hidden md:block">
        <button
          onClick={() => {
            setActivePopup(null);
            onOpenCommandPalette && onOpenCommandPalette();
          }}
          className="w-full h-9 flex items-center justify-between px-3.5 rounded-xl bg-slate-100/90 dark:bg-slate-900/90 border border-slate-200/80 dark:border-slate-800 text-xs text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
        >
          <div className="flex items-center gap-2 truncate">
            <Search className="w-3.5 h-3.5 text-slate-400 group-hover:text-indigo-500 shrink-0" />
            <span className="truncate">Search campaigns, rules, audiences...</span>
          </div>
          <kbd className="hidden sm:inline-flex items-center gap-0.5 px-2 py-0.5 text-[10px] font-semibold text-slate-400 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md shadow-2xs shrink-0">
            <Command className="w-3 h-3" />K
          </kbd>
        </button>
      </div>

      <div className="flex items-center gap-2 sm:gap-2.5 shrink-0">
        {isMetaConnected ? (
          <button
            onClick={() => {
              setActivePopup(null);
              onOpenFacebookOAuthModal();
            }}
            className="h-9 px-2.5 sm:px-3 rounded-xl bg-emerald-50/90 dark:bg-emerald-950/40 border border-emerald-200/80 dark:border-emerald-800/80 text-emerald-800 dark:text-emerald-200 text-xs font-semibold flex items-center gap-2"
          >
            <div className="w-5 h-5 rounded-md bg-blue-600 text-white flex items-center justify-center shrink-0">
              <Facebook className="w-3 h-3 fill-current" />
            </div>
            <span className="hidden sm:inline font-bold">Meta Connected</span>
          </button>
        ) : (
          <button
            onClick={() => {
              setActivePopup(null);
              onOpenFacebookOAuthModal();
            }}
            className="h-9 px-3.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-xs flex items-center gap-2"
          >
            <Facebook className="w-4 h-4 fill-current" />
            <span className="hidden sm:inline">Connect Meta Account</span>
          </button>
        )}

        {isMetaConnected && (
          <button
            onClick={() => {
              setActivePopup(null);
              onManualSync && onManualSync();
            }}
            disabled={isSyncing}
            className="h-9 px-3 rounded-xl text-xs font-semibold bg-slate-100/90 dark:bg-slate-900/90 text-slate-700 dark:text-slate-300 border border-slate-200/80 dark:border-slate-800"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin text-amber-500' : 'text-emerald-500'}`} />
          </button>
        )}

        {isMetaConnected && (
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => {
              setActivePopup(null);
              onOpenCopilot && onOpenCopilot();
            }}
            className="h-9 px-3.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-xs flex items-center gap-1.5"
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-300" />
            <span className="hidden sm:inline">AI Copilot</span>
          </motion.button>
        )}
      </div>
    </header>
  );
};

export default Header;
