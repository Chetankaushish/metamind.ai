import React, { createContext, useContext, useState } from 'react';

export interface OrgSettings {
  country: string;
  currency: string;
  timezone: string;
  locale: string;
  dateFormat: string;
  numberFormat: 'indian' | 'standard';
}

const defaultOrgSettings: OrgSettings = {
  country: 'India',
  currency: 'INR',
  timezone: 'Asia/Kolkata',
  locale: 'en-IN',
  dateFormat: 'DD/MM/YYYY',
  numberFormat: 'indian'
};

interface OrgSettingsContextType {
  settings: OrgSettings;
  updateSettings: (newSettings: Partial<OrgSettings>) => void;
}

const OrgSettingsContext = createContext<OrgSettingsContextType | undefined>(undefined);

export const OrgSettingsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [settings, setSettings] = useState<OrgSettings>(() => {
    try {
      const saved = localStorage.getItem('metamind_org_settings');
      return saved ? JSON.parse(saved) : defaultOrgSettings;
    } catch {
      return defaultOrgSettings;
    }
  });

  const updateSettings = (newSettings: Partial<OrgSettings>) => {
    setSettings((prev) => {
      const updated = { ...prev, ...newSettings };
      try {
        localStorage.setItem('metamind_org_settings', JSON.stringify(updated));
      } catch {}
      return updated;
    });
  };

  return (
    <OrgSettingsContext.Provider value={{ settings, updateSettings }}>
      {children}
    </OrgSettingsContext.Provider>
  );
};

export const useOrgSettings = () => {
  const context = useContext(OrgSettingsContext);
  if (!context) {
    return { settings: defaultOrgSettings, updateSettings: () => {} };
  }
  return context;
};
