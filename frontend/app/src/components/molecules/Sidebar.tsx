import React, { useState } from 'react';
import { Shield, LayoutDashboard, Settings, LogOut, HelpCircle, Menu, X, Video, Users } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useStreamingSession } from '../../context/StreamingSessionContext';
import { buildAppUrlForHashView } from '../../nav/appHash';
import { isBackendEnabled } from '../../services/apiBase';
import { Tutorial } from './Tutorial';

interface SidebarProps {
  currentView: string;
  onNavigate: (view: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentView, onNavigate }) => {
  const { user, logout, isAdmin } = useAuth();
  const { streamingActive } = useStreamingSession();
  const showUserAdmin = isAdmin && isBackendEnabled();
  const [showTutorial, setShowTutorial] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const handleNavigate = (view: string) => {
    const onStreamTab = currentView === 'camera-stream';
    const staysOnStreamUi = view === 'camera-stream';
    const deferToNewTab =
      streamingActive && onStreamTab && !staysOnStreamUi && view !== currentView;

    if (deferToNewTab) {
      window.open(buildAppUrlForHashView(view), '_blank', 'noopener,noreferrer');
      setIsMobileMenuOpen(false);
      return;
    }
    onNavigate(view);
    setIsMobileMenuOpen(false);
  };

  const handleOpenTutorial = () => {
    setShowTutorial(true);
    setIsMobileMenuOpen(false);
  };

  const sidebarContent = (
    <>
      <div>
        <div className="p-6 flex items-center gap-3">
          <Shield className="w-8 h-8 text-guardian-accent" />
          <span className="text-xl font-bold tracking-wider">Guardian</span>
        </div>
        
        <nav className="mt-6">
          <ul className="space-y-2 px-4">
            <li>
              <button 
                onClick={() => handleNavigate('dashboard')}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${currentView === 'dashboard' ? 'bg-gray-800/50 text-white' : 'text-guardian-muted hover:text-white hover:bg-gray-800/30'}`}
              >
                <LayoutDashboard className="w-5 h-5" />
                <span className="font-medium">Dashboard</span>
              </button>
            </li>
            <li>
              <button 
                onClick={() => handleNavigate('settings')}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${currentView === 'settings' ? 'bg-gray-800/50 text-white' : 'text-guardian-muted hover:text-white hover:bg-gray-800/30'}`}
              >
                <Settings className="w-5 h-5" />
                <span className="font-medium">Settings</span>
              </button>
            </li>
            {showUserAdmin && (
              <li>
                <button
                  type="button"
                  onClick={() => handleNavigate('admin-users')}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${currentView === 'admin-users' ? 'bg-gray-800/50 text-white' : 'text-guardian-muted hover:text-white hover:bg-gray-800/30'}`}
                >
                  <Users className="w-5 h-5" />
                  <span className="font-medium">Users</span>
                </button>
              </li>
            )}
            <li>
              <button
                onClick={() => handleNavigate('camera-stream')}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${currentView === 'camera-stream' ? 'bg-gray-800/50 text-white' : 'text-guardian-muted hover:text-white hover:bg-gray-800/30'}`}
              >
                <Video className="w-5 h-5" />
                <span className="font-medium">Camera Stream</span>
              </button>
            </li>
            <li>
              <button 
                onClick={handleOpenTutorial}
                className="w-full flex items-center gap-3 px-4 py-3 text-guardian-muted hover:text-white hover:bg-gray-800/30 rounded-lg transition-colors"
              >
                <HelpCircle className="w-5 h-5" />
                <span className="font-medium">Help / Tutorial</span>
              </button>
            </li>
          </ul>
        </nav>
      </div>

      <div className="p-6 border-t border-gray-800 flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center overflow-hidden font-bold text-lg">
              {user?.name?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="flex flex-col min-w-0">
              <span className="text-sm font-semibold truncate">{user?.name}</span>
              <span className="text-xs text-guardian-muted">{user?.roleLabel}</span>
            </div>
          </div>
        </div>
        
        <button 
          onClick={logout}
          className="w-full flex items-center gap-3 px-4 py-2 text-guardian-danger hover:bg-red-500/10 rounded-lg transition-colors"
        >
          <LogOut className="w-5 h-5" />
          <span className="font-medium">Logout</span>
        </button>
      </div>
    </>
  );

  return (
    <>
      {showTutorial && <Tutorial onClose={() => setShowTutorial(false)} />}
      <div className="hidden md:flex w-64 h-full bg-guardian-bg border-r border-gray-800 flex-col justify-between shrink-0">
        {sidebarContent}
      </div>

      <div className="md:hidden fixed top-0 left-0 right-0 z-40 border-b border-gray-800 bg-guardian-bg/95 backdrop-blur-sm">
        <div className="h-14 px-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="w-6 h-6 text-guardian-accent" />
            <span className="font-bold tracking-wider">Guardian</span>
          </div>
          <button
            type="button"
            className="p-2 rounded-lg hover:bg-gray-800/70 transition-colors"
            onClick={() => setIsMobileMenuOpen((prev) => !prev)}
            aria-label={isMobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
          >
            {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      <div className="md:hidden h-14 w-full shrink-0" />

      {isMobileMenuOpen && (
        <>
          <button
            type="button"
            className="md:hidden fixed inset-0 z-40 bg-black/50"
            aria-label="Close navigation menu"
            onClick={() => setIsMobileMenuOpen(false)}
          />
          <aside className="md:hidden fixed top-14 left-0 bottom-0 z-50 w-[85vw] max-w-sm bg-guardian-bg border-r border-gray-800 flex flex-col justify-between">
            {sidebarContent}
          </aside>
        </>
      )}
    </>
  );
};
