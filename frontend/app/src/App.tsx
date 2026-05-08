import { useState } from 'react';
import { MainLayout } from './layouts/MainLayout';
import { Dashboard } from './pages/Dashboard';
import { CameraView } from './pages/CameraView';
import { LoginPage } from './pages/LoginPage';
import { SettingsPage } from './pages/SettingsPage';
import { AddCameraPage } from './pages/AddCameraPage';
import { AuthProvider, useAuth } from './context/AuthContext';

function AppContent() {
  const { user } = useAuth();
  const [currentView, setCurrentView] = useState<'dashboard' | 'camera' | 'settings' | 'add-camera'>('dashboard');
  const [activeCameraId, setActiveCameraId] = useState<string | null>(null);

  if (!user) {
    return <LoginPage />;
  }

  const handleNavigate = (view: string) => {
    setCurrentView(view as any);
  };

  const handleViewCamera = (id: string) => {
    setActiveCameraId(id);
    setCurrentView('camera');
  };

  const handleBackToDashboard = () => {
    setActiveCameraId(null);
    setCurrentView('dashboard');
  };

  return (
    <MainLayout currentView={currentView} onNavigate={handleNavigate}>
      {currentView === 'dashboard' && <Dashboard onViewCamera={handleViewCamera} onAddCamera={() => setCurrentView('add-camera')} />}
      {currentView === 'settings' && <SettingsPage />}
      {currentView === 'add-camera' && <AddCameraPage onBack={handleBackToDashboard} />}
      {currentView === 'camera' && (
        <CameraView 
          cameraId={activeCameraId || 'CAM-001'} 
          onBack={handleBackToDashboard} 
        />
      )}
    </MainLayout>
  );
}

import { ToastProvider } from './context/ToastContext';

function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ToastProvider>
  );
}

export default App;
