import React from 'react';

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  title,
  description,
  action,
  className = ''
}) => {
  return (
    <div className={`flex flex-col items-center justify-center p-8 sm:p-12 text-center rounded-2xl border border-dashed border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/20 ${className}`}>
      {icon && (
        <div className="w-12 h-12 rounded-2xl bg-blue-500/10 dark:bg-blue-500/20 text-blue-600 dark:text-cyan-400 flex items-center justify-center mb-4 text-xl shadow-inner">
          {icon}
        </div>
      )}
      <h3 className="text-base font-bold text-slate-900 dark:text-white">{title}</h3>
      {description && (
        <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mt-1 mb-5">
          {description}
        </p>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
};
