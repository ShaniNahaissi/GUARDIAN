import React, { useState } from 'react';
import { Shield, LayoutDashboard, Settings, LogOut, HelpCircle } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Tutorial } from './Tutorial';

interface SidebarProps {
  currentView: string;
  onNavigate: (view: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentView, onNavigate }) => {
  const { user, logout } = useAuth();
  const [showTutorial, setShowTutorial] = useState(false);

  return (
    <>
      {showTutorial && <Tutorial onClose={() => setShowTutorial(false)} />}

      <div className="w-64 h-full bg-guardian-bg border-r border-gray-800 flex flex-col justify-between">
        <div>
          <div className="p-6 flex items-center gap-3">
            <Shield className="w-8 h-8 text-guardian-accent" />
            <span className="text-xl font-bold tracking-wider">Guardian</span>
          </div>
          
          <nav className="mt-6">
            <ul className="space-y-2 px-4">
              <li>
                <button 
                  onClick={() => onNavigate('dashboard')}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${currentView === 'dashboard' ? 'bg-gray-800/50 text-white' : 'text-guardian-muted hover:text-white hover:bg-gray-800/30'}`}
                >
                  <LayoutDashboard className="w-5 h-5" />
                  <span className="font-medium">Dashboard</span>
                </button>
              </li>
              <li>
                <button 
                  onClick={() => onNavigate('settings')}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${currentView === 'settings' ? 'bg-gray-800/50 text-white' : 'text-guardian-muted hover:text-white hover:bg-gray-800/30'}`}
                >
                  <Settings className="w-5 h-5" />
                  <span className="font-medium">Settings</span>
                </button>
              </li>
              <li>
                <button 
                  onClick={() => setShowTutorial(true)}
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
              <div className="flex flex-col">
                <span className="text-sm font-semibold truncate w-32">{user?.name}</span>
                <span className="text-xs text-guardian-muted">{user?.role}</span>
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
      </div>
    </>
  );
};
