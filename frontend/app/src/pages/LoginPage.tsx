import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Shield } from 'lucide-react';
import { Button } from '../components/atoms/Button';
import { Card } from '../components/atoms/Card';

export const LoginPage: React.FC = () => {
  const { login, register, authError, clearAuthError } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (isLogin) {
        await login(username, password);
      } else {
        await register(username, password, name);
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-guardian-bg flex flex-col items-center justify-center p-4">
      <div className="flex items-center gap-3 mb-8">
        <Shield className="w-12 h-12 text-guardian-accent" />
        <span className="text-4xl font-bold tracking-wider text-white">Guardian</span>
      </div>

      <Card className="w-full max-w-md p-8">
        <h2 className="text-2xl font-bold mb-6 text-center text-white">
          {isLogin ? 'Welcome Back' : 'Create Account'}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <div>
              <label className="block text-sm font-medium text-guardian-muted mb-1">Full Name</label>
              <input 
                type="text" 
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-guardian-accent"
                required={!isLogin}
              />
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-guardian-muted mb-1">Username</label>
            <input 
              type="text" 
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-guardian-accent"
              required 
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-guardian-muted mb-1">Password</label>
            <input 
              type="password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-guardian-accent"
              required 
            />
          </div>

          <Button type="submit" className="w-full mt-6" disabled={busy}>
            {busy ? 'Please wait…' : isLogin ? 'Login' : 'Register'}
          </Button>
        </form>

        {authError && (
          <p className="mt-4 text-sm text-guardian-danger text-center" role="alert">
            {authError}
          </p>
        )}

        <div className="mt-6 text-center">
          <button
            type="button"
            onClick={() => {
              clearAuthError();
              setIsLogin(!isLogin);
            }}
            className="text-sm text-guardian-accent hover:underline"
          >
            {isLogin ? 'Need an account? Register' : 'Already have an account? Login'}
          </button>
        </div>
      </Card>
    </div>
  );
};
