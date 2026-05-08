import React, { useState } from 'react';
import { X, ArrowRight, ArrowLeft, Shield, LayoutDashboard, Camera, Settings, Bell } from 'lucide-react';

interface TutorialStep {
  title: string;
  description: string;
  icon: React.ReactNode;
  highlight?: string;
}

const STEPS: TutorialStep[] = [
  {
    title: 'Welcome to Guardian',
    description: 'Guardian is your real-time weapon detection system. It monitors camera feeds, detects threats, and helps you respond fast. This tutorial will walk you through all the major features.',
    icon: <Shield className="w-12 h-12 text-guardian-accent" />,
  },
  {
    title: 'The Dashboard',
    description: 'The Dashboard shows all your camera feeds at a glance. You can see the threat level of each camera, filter by severity (Critical, Warning, Normal), refresh feeds, and add new cameras.',
    icon: <LayoutDashboard className="w-12 h-12 text-guardian-accent" />,
    highlight: 'Tip: Use the Filter button to quickly find cameras with active threats.',
  },
  {
    title: 'Camera View',
    description: 'Click "View" on any camera card to enter the Camera View. Here you can see the live feed in full detail, threat detection overlays, and the Threat Panel on the right with AI analysis.',
    icon: <Camera className="w-12 h-12 text-guardian-accent" />,
    highlight: 'Tip: Use the Record button to start capturing footage. Click Stop Record to finish and send the video to the backend.',
  },
  {
    title: 'Alerts & Actions',
    description: 'When a threat is detected, a red Alert Banner appears at the top of the camera view. You can close it once acknowledged. Each camera card also has an Alert button to manually flag an incident.',
    icon: <Bell className="w-12 h-12 text-guardian-danger" />,
    highlight: 'Tip: Click Snapshot on the Camera View to instantly capture and log an image of a detected threat.',
  },
  {
    title: 'Settings',
    description: 'Go to Settings from the sidebar to configure the data source. By default, Guardian uses the Backend API. You can switch to Mock Data for development and testing without a live backend.',
    icon: <Settings className="w-12 h-12 text-guardian-accent" />,
    highlight: 'Tip: The Backend URL defaults from the .env file but can be overridden in Settings.',
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
