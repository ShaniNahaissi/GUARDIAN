import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'danger' | 'secondary';
  children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({ variant = 'primary', children, className = '', ...props }) => {
  const baseStyles = 'px-4 py-2 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2';
  
  const variants = {
    primary: 'bg-guardian-accent hover:bg-blue-600 text-white',
    danger: 'bg-guardian-danger hover:bg-red-600 text-white',
    secondary: 'bg-gray-800 hover:bg-gray-700 text-white',
  };

  return (
    <button className={`${baseStyles} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
};
