import React from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(({
  label,
  error,
  helperText,
  leftIcon,
  rightIcon,
  className = '',
  id,
  ...props
}, ref) => {
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className="flex flex-col gap-1.5 w-full">
      {label && (
        <label htmlFor={inputId} className="text-xs font-semibold text-slate-700 dark:text-slate-300">
          {label}
        </label>
      )}
      <div className="relative flex items-center">
        {leftIcon && (
          <div className="absolute left-3 text-slate-400 dark:text-slate-500 pointer-events-none flex items-center">
            {leftIcon}
          </div>
        )}
        <input
          id={inputId}
          ref={ref}
          className={`w-full rounded-lg border bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 text-sm transition-all duration-200 placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 ${
            error
              ? 'border-rose-500 focus:border-rose-500 focus:ring-rose-500/30'
              : 'border-slate-200 dark:border-slate-800 focus:border-blue-500'
          } ${leftIcon ? 'pl-9' : 'pl-3.5'} ${rightIcon ? 'pr-9' : 'pr-3.5'} py-2 ${className}`}
          {...props}
        />
        {rightIcon && (
          <div className="absolute right-3 text-slate-400 dark:text-slate-500 flex items-center">
            {rightIcon}
          </div>
        )}
      </div>
      {error && <span className="text-xs font-medium text-rose-500">{error}</span>}
      {!error && helperText && <span className="text-xs text-slate-500 dark:text-slate-400">{helperText}</span>}
    </div>
  );
});

Input.displayName = 'Input';
