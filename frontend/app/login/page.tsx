'use client';

import { useState } from 'react';
import LoginPage from '@/app/components/LoginPage';
import RegistrationPage from '@/app/components/RegistrationPage';

export default function Login() {
  const [showRegistration, setShowRegistration] = useState(false);

  const handleShowRegistration = () => setShowRegistration(true);
  const handleBackToLogin = () => setShowRegistration(false);

  return showRegistration ? (
    <RegistrationPage onBackToLogin={handleBackToLogin} />
  ) : (
    <LoginPage onShowRegistration={handleShowRegistration} />
  );
}
