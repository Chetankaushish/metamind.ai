import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { X, ShieldCheck, Laptop, Smartphone, Clock, LogOut } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';

interface SessionManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SessionManagerModal: React.FC<SessionManagerModalProps> = ({ isOpen, onClose }) => {
  const { user, logout } = useAuth();

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 10 }}
          className="relative w-full max-w-lg p-6 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl shadow-2xl space-y-5"
        >
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-500">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h2 className="text-base font-extrabold text-slate-900 dark:text-slate-100">Active User Sessions</h2>
            </div>
            <button
              onClick={onClose}
              className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-3">
            <div className="p-4 rounded-2xl bg-indigo-50/50 dark:bg-indigo-950/30 border border-indigo-200/80 dark:border-indigo-800/50 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Laptop className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                <div>
                  <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100">
                    Current Session (Mac OS / Chrome)
                  </h4>
                  <p className="text-[11px] text-slate-500 flex items-center gap-1 mt-0.5">
                    <Clock className="w-3 h-3" /> Active Now • {user?.email || 'admin@volzad.com'}
                  </p>
                </div>
              </div>
              <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 text-[10px] font-extrabold uppercase">
                Active
              </span>
            </div>

            <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/60 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Smartphone className="w-5 h-5 text-slate-400" />
                <div>
                  <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100">
                    Mobile App (iOS / Meta SDK)
                  </h4>
                  <p className="text-[11px] text-slate-500 flex items-center gap-1 mt-0.5">
                    <Clock className="w-3 h-3" /> Last active 2 hours ago
                  </p>
                </div>
              </div>
              <button
                onClick={async () => {
                  await logout();
                  onClose();
                }}
                className="px-3 py-1 rounded-xl bg-slate-200 dark:bg-slate-700 hover:bg-rose-500 hover:text-white text-xs font-bold text-slate-700 dark:text-slate-200 transition cursor-pointer flex items-center gap-1"
              >
                <LogOut className="w-3 h-3" /> Terminate
              </button>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-bold border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 transition cursor-pointer"
            >
              Close Window
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default SessionManagerModal;
