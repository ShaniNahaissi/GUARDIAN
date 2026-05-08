import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export const Card: React.FC<CardProps> = ({ children, className = '' }) => {
  return (
    <div className={`bg-guardian-card rounded-xl border border-gray-800 shadow-lg overflow-hidden ${className}`}>
      {children}
    </div>
  );
};
