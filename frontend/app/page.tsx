'use client';

import { useState } from 'react';
import { useAuth } from '@/hooks/use-auth';
import LoginPage from '@/app/components/LoginPage';
import RegistrationPage from '@/app/components/RegistrationPage';
import Dashboard from '@/app/components/Dashboard';

export default function App() {
  const { user, loading } = useAuth();
  const [showRegistration, setShowRegistration] = useState(false);

  const handleShowRegistration = () => {
    setShowRegistration(true);
  };

  const handleBackToLogin = () => {
    setShowRegistration(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-lg font-medium text-gray-600">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {!user ? (
        showRegistration ? (
          <RegistrationPage 
            onBackToLogin={handleBackToLogin}
          />
        ) : (
          <LoginPage 
            onShowRegistration={handleShowRegistration}
          />
        )
      ) : (
        <Dashboard user={user} />
      )}
    </div>
  );
}
