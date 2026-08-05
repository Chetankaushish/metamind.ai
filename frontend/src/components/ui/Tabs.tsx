import React, { createContext, useContext, useState } from 'react';

interface TabsContextType {
  activeTab: string;
  setActiveTab: (value: string) => void;
}

const TabsContext = createContext<TabsContextType | undefined>(undefined);

export interface TabsProps {
  defaultValue: string;
  value?: string;
  onValueChange?: (value: string) => void;
  children: React.ReactNode;
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({
  defaultValue,
  value,
  onValueChange,
  children,
  className = ''
}) => {
  const [selectedTab, setSelectedTab] = useState(defaultValue);
  const activeTab = value !== undefined ? value : selectedTab;

  const setActiveTab = (val: string) => {
    if (value === undefined) setSelectedTab(val);
    onValueChange?.(val);
  };

  return (
    <TabsContext.Provider value={{ activeTab, setActiveTab }}>
      <div className={`flex flex-col gap-4 ${className}`}>{children}</div>
    </TabsContext.Provider>
  );
};

export const TabsList: React.FC<{ children: React.ReactNode; className?: string }> = ({
  children,
  className = ''
}) => (
  <div className={`inline-flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-800/80 rounded-xl border border-slate-200/50 dark:border-slate-700/50 ${className}`}>
    {children}
  </div>
);

export interface TabsTriggerProps {
  value: string;
  children: React.ReactNode;
  className?: string;
  icon?: React.ReactNode;
}

export const TabsTrigger: React.FC<TabsTriggerProps> = ({
  value,
  children,
  className = '',
  icon
}) => {
  const context = useContext(TabsContext);
  if (!context) throw new Error('TabsTrigger must be used within Tabs');

  const isActive = context.activeTab === value;

  return (
    <button
      onClick={() => context.setActiveTab(value)}
      className={`inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${
        isActive
          ? 'bg-white dark:bg-slate-900 text-blue-600 dark:text-cyan-400 shadow-sm border border-slate-200/80 dark:border-slate-700/80 font-bold'
          : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/50 dark:hover:bg-slate-700/40'
      } ${className}`}
    >
      {icon}
      <span>{children}</span>
    </button>
  );
};

export interface TabsContentProps {
  value: string;
  children: React.ReactNode;
  className?: string;
}

export const TabsContent: React.FC<TabsContentProps> = ({ value, children, className = '' }) => {
  const context = useContext(TabsContext);
  if (!context) throw new Error('TabsContent must be used within Tabs');

  if (context.activeTab !== value) return null;

  return <div className={`animate-in fade-in duration-200 ${className}`}>{children}</div>;
};
