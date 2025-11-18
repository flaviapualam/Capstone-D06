'use client';

import { useState } from 'react';
import { Button } from './ui/button';
import { LogOut, Plus, Tag } from 'lucide-react';
import { useAuth } from '@/hooks/use-auth';
import { User } from '@/types';
import RecordDataSection from './RecordDataSection';
import ChooseCowSection from './ChooseCowSection';
import MonitoringSection from './MonitoringSection';
import AlertsSection from './AlertsSection';
import CattleRegistrationModal from './CattleRegistrationModal';
import RfidAssignmentModal from './RfidAssignmentModal';
import Toast, { useToast } from './Toast';

interface DashboardProps {
  user: User;
}

export default function Dashboard({ user }: DashboardProps) {
  const [showRegistrationModal, setShowRegistrationModal] = useState(false);
  const [showRfidAssignmentModal, setShowRfidAssignmentModal] = useState(false);
  const [selectedCowName, setSelectedCowName] = useState<string>('');
  const [selectedCowId, setSelectedCowId] = useState<string | undefined>(undefined);
  const [refreshCattle, setRefreshCattle] = useState(false);
  const { logout } = useAuth();
  const { toasts, showToast, removeToast } = useToast();

  const handleCattleRegistered = () => {
    setRefreshCattle(!refreshCattle);
    setShowRegistrationModal(false);
  };

  const handleRfidAssigned = () => {
    setRefreshCattle(!refreshCattle);
    setShowRfidAssignmentModal(false);
  };

  const handleCowSelect = (cowName: string, cowId?: string) => {
    setSelectedCowName(cowName);
    setSelectedCowId(cowId);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-0">
              <img 
                src="/logo.png" 
                alt="Cattle Farm Logo" 
                className="h-24 w-24"
              />
              <h1 className="text-xl font-semibold text-gray-900">
                CATTLE Management System
              </h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">Welcome, {user.name}</span>
              
              {/* Alerts Section in Navbar */}
              <AlertsSection />
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowRegistrationModal(true)}
                className="flex items-center space-x-2 text-emerald-600 hover:text-emerald-700 border-emerald-200 hover:border-emerald-300"
              >
                <Plus className="w-4 h-4" />
                <span>Add Cow</span>
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowRfidAssignmentModal(true)}
                  className="flex items-center space-x-2 text-emerald-600 hover:text-emerald-700 border-emerald-200 hover:border-emerald-300"
              >
                <Tag className="w-4 h-4" />
                <span>Assign RFID</span>
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                onClick={logout}
                className="flex items-center space-x-2 text-red-600 hover:text-red-700 border-red-200 hover:border-red-300"
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
          {/* Welcome Section */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Welcome back, {user.name}!
            </h2>
            <p className="text-gray-600">
              Monitor your cattle health, activity, and feed intake from your dashboard.
            </p>
          </div>
          
          {/* Monitoring Section */}
          {/* <MonitoringSection /> */}

          {/* Choose Cow Section */}
          <ChooseCowSection 
            selectedCowName={selectedCowName}
            onCowSelect={handleCowSelect}
            onCattleUpdated={handleCattleRegistered}
            onSuccess={showToast}
            refreshTrigger={refreshCattle}
          />
          
          {/* Record Data Section */}
          <RecordDataSection 
            selectedCowName={selectedCowName} 
            selectedCowId={selectedCowId}
          />
        </div>
      </main>

      {/* Registration Modal */}
      <CattleRegistrationModal
        isOpen={showRegistrationModal}
        onClose={() => setShowRegistrationModal(false)}
        onCattleRegistered={handleCattleRegistered}
        onSuccess={showToast}
      />

      {/* RFID Assignment Modal */}
      <RfidAssignmentModal
        isOpen={showRfidAssignmentModal}
        onClose={() => setShowRfidAssignmentModal(false)}
        onRfidAssigned={handleRfidAssigned}
        onSuccess={showToast}
        refreshTrigger={refreshCattle}
      />

      {/* Toasts */}
      <Toast toasts={toasts} onRemove={removeToast} />
    </div>
  );
}