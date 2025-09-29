'use client';

import LoginPage from '@/app/components/LoginPage';
import { useRouter } from 'next/navigation';

export default function Login() {
  const router = useRouter();

  const handleShowRegistration = () => {
    // You can implement registration logic here or navigate to a registration page
    console.log('Show registration clicked');
  };

  return <LoginPage onShowRegistration={handleShowRegistration} />;
}
