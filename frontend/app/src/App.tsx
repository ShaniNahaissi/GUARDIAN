import { useState } from 'react';
import { MainLayout } from './layouts/MainLayout';
import { Dashboard } from './pages/Dashboard';
import { CameraView } from './pages/CameraView';
import { LoginPage } from './pages/LoginPage';
import { SettingsPage } from './pages/SettingsPage';
import { AddCameraPage } from './pages/AddCameraPage';
import { EditCameraPage } from './pages/EditCameraPage';
import { CameraStreamPage } from './pages/CameraStreamPage';
import { AdminUsersPage } from './pages/AdminUsersPage';
import { AuthProvider, useAuth } from './context/AuthContext';

type AppView = 'dashboard' | 'camera' | 'settings' | 'add-camera' | 'edit-camera' | 'camera-stream' | 'admin-users';

function AppContent() {
  const { user, sessionRestored } = useAuth();
  const [currentView, setCurrentView] = useState<AppView>('dashboard');
  const [activeCameraId, setActiveCameraId] = useState<string | null>(null);

  if (!sessionRestored) {
    return (
      <div className="min-h-screen bg-guardian-bg flex items-center justify-center text-guardian-muted text-sm">
        Loading session…
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  const handleNavigate = (view: string) => {
    setCurrentView(view as AppView);
  };

  const handleViewCamera = (id: string) => {
    setActiveCameraId(id);
    setCurrentView('camera');
  };

  const handleEditCamera = (id: string) => {
    setActiveCameraId(id);
    setCurrentView('edit-camera');
  };

  const handleBackToDashboard = () => {
    setActiveCameraId(null);
    setCurrentView('dashboard');
  };

  return (
    <MainLayout currentView={currentView} onNavigate={handleNavigate}>
      {currentView === 'dashboard' && <Dashboard onViewCamera={handleViewCamera} onAddCamera={() => setCurrentView('add-camera')} onEditCamera={handleEditCamera} />}
      {currentView === 'settings' && <SettingsPage />}
      {currentView === 'admin-users' && <AdminUsersPage onBack={handleBackToDashboard} />}
      {currentView === 'add-camera' && <AddCameraPage onBack={handleBackToDashboard} />}
      {currentView === 'edit-camera' && activeCameraId && <EditCameraPage cameraId={activeCameraId} onBack={handleBackToDashboard} />}
      {currentView === 'camera-stream' && <CameraStreamPage onBack={handleBackToDashboard} />}
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
