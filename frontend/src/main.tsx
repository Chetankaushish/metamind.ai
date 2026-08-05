import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.tsx';
import './styles/index.css';
import { ThemeProvider } from './contexts/ThemeContext.tsx';
import { OrgSettingsProvider } from './contexts/OrgSettingsContext.tsx';
import { AuthProvider } from './contexts/AuthContext.tsx';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <ThemeProvider>
        <OrgSettingsProvider>
          <App />
        </OrgSettingsProvider>
      </ThemeProvider>
    </AuthProvider>
  </StrictMode>,
);
