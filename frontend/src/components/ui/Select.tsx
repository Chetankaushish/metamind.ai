import React from 'react';

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: SelectOption[];
  error?: string;
  helperText?: string;
  icon?: React.ReactNode;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(({
  label,
  options,
  error,
  helperText,
  icon,
  className = '',
  id,
  ...props
}, ref) => {
  const selectId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className="flex flex-col gap-1.5 w-full">
      {label && (
        <label htmlFor={selectId} className="text-xs font-semibold text-slate-700 dark:text-slate-300">
          {label}
        </label>
      )}
      <div className="relative flex items-center">
        {icon && (
          <div className="absolute left-3 text-slate-400 dark:text-slate-500 pointer-events-none flex items-center">
            {icon}
          </div>
        )}
        <select
          id={selectId}
          ref={ref}
          className={`w-full appearance-none rounded-lg border bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-sm transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 ${
            error
              ? 'border-rose-500 focus:border-rose-500 focus:ring-rose-500/30'
              : 'border-slate-200 dark:border-slate-800 focus:border-blue-500'
          } ${icon ? 'pl-9' : 'pl-3.5'} pr-9 py-2 cursor-pointer ${className}`}
          {...props}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value} disabled={opt.disabled}>
              {opt.label}
            </option>
          ))}
        </select>
        <div className="absolute right-3 pointer-events-none text-slate-400 dark:text-slate-500">
          <svg className="w-4 h-4 fill-current" viewBox="0 0 20 20">
            <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
          </svg>
        </div>
      </div>
      {error && <span className="text-xs font-medium text-rose-500">{error}</span>}
      {!error && helperText && <span className="text-xs text-slate-500 dark:text-slate-400">{helperText}</span>}
    </div>
  );
});

Select.displayName = 'Select';
