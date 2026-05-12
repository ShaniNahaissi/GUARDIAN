import React, { useState } from 'react';
import {
  X,
  ArrowRight,
  ArrowLeft,
  Shield,
  LayoutDashboard,
  Camera,
  Settings,
  Video,
  Users,
  LogIn,
} from 'lucide-react';

interface TutorialStep {
  title: string;
  description: string;
  icon: React.ReactNode;
  highlight?: string;
}

const STEPS: TutorialStep[] = [
  {
    title: 'Welcome to Guardian',
    description:
      'Guardian is a real-time monitoring UI for camera streams processed by the backend (ONNX detection, tracking, and alerts). You sign in, review the dashboard, open individual cameras, and optionally manage users if you are an administrator.',
    icon: <Shield className="w-12 h-12 text-guardian-accent" />,
    highlight: 'Use Next to step through the product, or ✕ to close anytime.',
  },
  {
    title: 'Sign in & roles',
    description:
      'With the backend API turned on in Settings, you log in with your account. New self-registration creates a viewer: you can browse dashboards and streams but not add servers. Operators and administrators can use Add server on the dashboard. Administrators also see Users in the sidebar to create accounts and change roles.',
    icon: <LogIn className="w-12 h-12 text-guardian-accent" />,
    highlight:
      'Typical Docker bootstrap admin is username Admin and password admin—change the password in production. With mock data enabled you get a simplified offline login (no API).',
  },
  {
    title: 'Dashboard',
    description:
      'The home view lists camera cards with status, location, and a View action. Filter by threat label, refresh the list from the API, and add a server entry when your role allows it (links a display name and stream UUID to the backend list).',
    icon: <LayoutDashboard className="w-12 h-12 text-guardian-accent" />,
    highlight: 'If Add server is missing, your account is a viewer—ask an admin to grant operator or admin.',
  },
  {
    title: 'Camera Stream',
    description:
      'Open Camera Stream in the sidebar to work with live WebSockets: the browser can send frames to the backend producer and receive processed JPEG plus track JSON on the consumer for the same stream id. Use the same UUID here as when adding a server on the dashboard.',
    icon: <Video className="w-12 h-12 text-guardian-accent" />,
    highlight: 'In local Vite dev, keep the backend URL as /api so TLS and WebSocket proxying stay consistent.',
  },
  {
    title: 'Camera View & alerts',
    description:
      'From a card, choose View for a focused layout: live preview, threat panel, Record / Snapshot actions, and an alert banner you can dismiss after triage. Camera cards can also surface manual alert controls depending on configuration.',
    icon: <Camera className="w-12 h-12 text-guardian-accent" />,
    highlight: 'Record toggles capture UI; Snapshot logs a still—both are wired for future backend persistence.',
  },
  {
    title: 'User management (admins)',
    description:
      'If you are signed in as an administrator with the backend enabled, Users appears in the sidebar. There you can list accounts, add users with passwords and roles, edit roles or names, reset passwords, and delete users (you cannot remove yourself or the last admin).',
    icon: <Users className="w-12 h-12 text-guardian-accent" />,
    highlight: 'Viewers never see this menu; it is hidden in mock-only mode.',
  },
  {
    title: 'Settings & data source',
    description:
      'Settings controls whether the app calls the real Guardian API or uses built-in mock cameras and stats. You can also override the backend base URL (for packaged builds, dev often uses /api behind HTTPS).',
    icon: <Settings className="w-12 h-12 text-guardian-accent" />,
    highlight: 'After changing URL or toggling mock/backend, refresh the dashboard so lists and auth line up with the new target.',
  },
];

interface TutorialProps {
  onClose: () => void;
}

export const Tutorial: React.FC<TutorialProps> = ({ onClose }) => {
  const [step, setStep] = useState(0);
  const currentStep = STEPS[step];
  const isFirst = step === 0;
  const isLast = step === STEPS.length - 1;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-guardian-card border border-gray-700 rounded-2xl shadow-2xl w-full max-w-lg mx-4 p-8 relative">
        {/* Close */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-guardian-muted hover:text-white transition-colors"
          aria-label="Close tutorial"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Progress dots */}
        <div className="flex gap-2 mb-8 justify-center">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-2 rounded-full transition-all duration-300 ${i === step ? 'w-8 bg-guardian-accent' : 'w-2 bg-gray-600'}`}
            />
          ))}
        </div>

        {/* Content */}
        <div className="flex flex-col items-center text-center gap-5">
          {currentStep.icon}
          <h2 className="text-2xl font-bold text-white">{currentStep.title}</h2>
          <p className="text-guardian-muted leading-relaxed">{currentStep.description}</p>
          {currentStep.highlight && (
            <div className="bg-guardian-accent/10 border border-guardian-accent/30 rounded-lg px-4 py-3 text-sm text-guardian-accent text-left w-full">
              {currentStep.highlight}
            </div>
          )}
        </div>

        {/* Navigation */}
        <div className="flex justify-between items-center mt-8">
          <button
            onClick={() => setStep(s => s - 1)}
            disabled={isFirst}
            className="flex items-center gap-2 px-4 py-2 text-guardian-muted hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back
          </button>

          <span className="text-xs text-guardian-muted">{step + 1} / {STEPS.length}</span>

          {isLast ? (
            <button
              onClick={onClose}
              className="flex items-center gap-2 px-6 py-2 bg-guardian-accent text-white rounded-lg font-medium hover:bg-blue-600 transition-colors"
            >
              Get Started
            </button>
          ) : (
            <button
              onClick={() => setStep(s => s + 1)}
              className="flex items-center gap-2 px-4 py-2 text-guardian-accent hover:text-white transition-colors"
            >
              Next <ArrowRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
