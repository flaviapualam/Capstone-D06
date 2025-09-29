'use client';

import { useState } from 'react';
import { Button } from './ui/button';
import { LogOut, Plus } from 'lucide-react';
import { useAuth } from '@/hooks/use-auth';
import { User } from '@/types';
import RecordDataSection from './RecordDataSection';
import ChooseCowSection from './ChooseCowSection';
import MonitoringSection from './MonitoringSection';
import AlertsSection from './AlertsSection';
import CattleRegistrationModal from './CattleRegistrationModal';

interface DashboardProps {
  user: User;
}

export default function Dashboard({ user }: DashboardProps) {
  const [showRegistrationModal, setShowRegistrationModal] = useState(false);
  const [selectedCowId, setSelectedCowId] = useState<string>('');
  const { logout } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <h1 className="text-xl font-semibold text-gray-900">
                Cattle Farm Management System
              </h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">Welcome, {user.name}</span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowRegistrationModal(true)}
                className="flex items-center space-x-2"
              >
                <Plus className="w-4 h-4" />
                <span>Add Cattle</span>
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={logout}
                className="flex items-center space-x-2"
              >
                <LogOut className="w-4 h-4" />
                <span>Logout</span>
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-8">
          {/* Alerts Section */}
          <AlertsSection />
          
          {/* Record Data Section */}
          <RecordDataSection selectedCowId={selectedCowId} />

          {/* Choose Cow Section */}
          <ChooseCowSection 
            selectedCowId={selectedCowId}
            onCowSelect={setSelectedCowId}
          />

          {/* Monitoring Section */}
          <MonitoringSection />

        </div>
      </main>

      {/* Registration Modal */}
      <CattleRegistrationModal
        isOpen={showRegistrationModal}
        onClose={() => setShowRegistrationModal(false)}
        onCattleRegistered={(cattle) => {
          console.log('New cattle registered:', cattle);
          setShowRegistrationModal(false);
        }}
      />
    </div>
  );
}