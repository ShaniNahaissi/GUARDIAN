import React from 'react';
import { Sidebar } from '../components/molecules/Sidebar';

interface MainLayoutProps {
  children: React.ReactNode;
  currentView: string;
  onNavigate: (view: string) => void;
}

export const MainLayout: React.FC<MainLayoutProps> = ({ children, currentView, onNavigate }) => {
  return (
    <div className="flex h-dvh w-full flex-col md:flex-row bg-guardian-bg text-guardian-text overflow-hidden">
      <Sidebar currentView={currentView} onNavigate={onNavigate} />
      <main className="flex-1 min-w-0 overflow-y-auto p-4 sm:p-6">
        {children}
      </main>
    </div>
  );
};
