import React from 'react';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverEffect?: boolean;
  glass?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  hoverEffect = false,
  glass = false,
  ...props
}) => {
  return (
    <div
      className={`rounded-xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-slate-900/90 text-slate-900 dark:text-slate-100 shadow-sm ${
        glass ? 'backdrop-blur-md bg-white/70 dark:bg-slate-900/80' : ''
      } ${
        hoverEffect ? 'transition-all duration-200 hover:shadow-md hover:border-slate-300 dark:hover:border-slate-700/80' : ''
      } ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

export const CardHeader: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  children,
  className = '',
  ...props
}) => (
  <div className={`p-5 pb-3 flex flex-col gap-1 border-b border-slate-100 dark:border-slate-800/60 ${className}`} {...props}>
    {children}
  </div>
);

export const CardTitle: React.FC<React.HTMLAttributes<HTMLHeadingElement>> = ({
  children,
  className = '',
  ...props
}) => (
  <h3 className={`text-base font-bold tracking-tight text-slate-900 dark:text-white ${className}`} {...props}>
    {children}
  </h3>
);

export const CardDescription: React.FC<React.HTMLAttributes<HTMLParagraphElement>> = ({
  children,
  className = '',
  ...props
}) => (
  <p className={`text-xs text-slate-500 dark:text-slate-400 ${className}`} {...props}>
    {children}
  </p>
);

export const CardContent: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  children,
  className = '',
  ...props
}) => (
  <div className={`p-5 ${className}`} {...props}>
    {children}
  </div>
);

export const CardFooter: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  children,
  className = '',
  ...props
}) => (
  <div className={`p-4 pt-3 border-t border-slate-100 dark:border-slate-800/60 flex items-center justify-between ${className}`} {...props}>
    {children}
  </div>
);
