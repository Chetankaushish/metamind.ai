import React, { useState } from "react";
import Header from "../components/common/Header";
import Sidebar, { NavTab } from "../components/common/Sidebar";

interface DashboardLayoutProps {
  children: React.ReactNode;

  activeTab: NavTab;
  setActiveTab: (tab: NavTab) => void;

  user: any;

  businessManagers: any[];
  selectedBm: any;
  setSelectedBm: (bm: any) => void;

  adAccounts: any[];
  selectedAccount: any;
  setSelectedAccount: (acc: any) => void;

  isMetaConnected: boolean;
  setIsMetaConnected: (val: boolean) => void;

  onOpenFacebookOAuthModal: () => void;

  onOpenAuthModal?: () => void;
  onOpenSessionModal?: () => void;

  onManualSync?: () => void;
  isSyncing?: boolean;
}

const DashboardLayout: React.FC<DashboardLayoutProps> = ({
  children,

  activeTab,
  setActiveTab,

  user,

  businessManagers,
  selectedBm,
  setSelectedBm,

  adAccounts,
  selectedAccount,
  setSelectedAccount,

  isMetaConnected,
  setIsMetaConnected,

  onOpenFacebookOAuthModal,

  onOpenAuthModal,
  onOpenSessionModal,

  onManualSync,
  isSyncing = false,
}) => {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex h-screen bg-slate-950 text-white">
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        collapsed={collapsed}
        setCollapsed={setCollapsed}
        isMetaConnected={isMetaConnected}
        user={user}
        onOpenFacebookOAuthModal={onOpenFacebookOAuthModal}
        onOpenAuthModal={onOpenAuthModal}
        onOpenSessionModal={onOpenSessionModal}
      />

      <div
        className={`flex flex-col flex-1 transition-all duration-300 ${
          collapsed ? "ml-16" : "ml-64"
        }`}
      >
        <Header
          isMetaConnected={isMetaConnected}
          setIsMetaConnected={setIsMetaConnected}

          businessManagers={businessManagers}
          selectedBm={selectedBm}
          setSelectedBm={setSelectedBm}

          adAccounts={adAccounts}
          selectedAccount={selectedAccount}
          setSelectedAccount={setSelectedAccount}

          user={user}

          onManualSync={onManualSync}
          isSyncing={isSyncing}

          activeTab={activeTab}

          onOpenFacebookOAuthModal={onOpenFacebookOAuthModal}
        />

        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;