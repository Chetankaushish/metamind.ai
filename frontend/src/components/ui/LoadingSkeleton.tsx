import React from 'react';

export const Skeleton: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className = '',
  ...props
}) => {
  return (
    <div
      className={`animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800 ${className}`}
      {...props}
    />
  );
};

export const CardSkeleton: React.FC = () => (
  <div className="p-6 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex flex-col gap-4">
    <div className="flex items-center justify-between">
      <Skeleton className="h-4 w-32" />
      <Skeleton className="h-6 w-16 rounded-full" />
    </div>
    <Skeleton className="h-8 w-24" />
    <Skeleton className="h-3 w-48" />
  </div>
);

export const TableSkeleton: React.FC<{ rows?: number }> = ({ rows = 5 }) => (
  <div className="w-full rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 flex flex-col gap-3">
    <Skeleton className="h-8 w-full rounded-lg" />
    {Array.from({ length: rows }).map((_, i) => (
      <Skeleton key={i} className="h-12 w-full rounded-lg" />
    ))}
  </div>
);
