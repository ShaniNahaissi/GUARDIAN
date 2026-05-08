import React from 'react';

interface BadgeProps {
  status: 'normal' | 'warning' | 'major' | 'critical';
  children: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({ status, children }) => {
  const styles = {
    normal: 'bg-guardian-success text-white',
    warning: 'bg-guardian-warning text-white',
    major: 'bg-orange-500 text-white',
    critical: 'bg-guardian-danger text-white',
  };

  return (
    <span className={`px-2 py-1 text-xs font-bold rounded flex items-center gap-1 ${styles[status]}`}>
      {children}
    </span>
  );
};
