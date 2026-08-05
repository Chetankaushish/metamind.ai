import React from 'react';

interface AppRoutesProps {
  activeView: string;
  viewsMap: Record<string, React.ReactNode>;
}

export const AppRoutes: React.FC<AppRoutesProps> = ({ activeView, viewsMap }) => {
  return <>{viewsMap[activeView] || viewsMap['dashboard']}</>;
};

export default AppRoutes;
