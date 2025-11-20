'use client';

import { useState, useCallback } from 'react';
import { Button } from './ui/button';
import { LogOut, Plus, Tag, Menu, X } from 'lucide-react';
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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { logout } = useAuth();
  const { toasts, showToast, removeToast } = useToast();

  const handleCattleRegistered = useCallback(() => {
    setRefreshCattle(prev => !prev);
    setShowRegistrationModal(false);
  }, []);

  const handleRfidAssigned = useCallback(() => {
    setRefreshCattle(prev => !prev);
    setShowRfidAssignmentModal(false);
  }, []);

  const handleCowSelect = useCallback((cowName: string, cowId?: string) => {
    setSelectedCowName(cowName);
    setSelectedCowId(cowId);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo + Title */}
            <div className="flex items-center space-x-0">
              <img 
                src="/logo.png" 
                alt="Cattle Farm Logo" 
                className="h-24 w-24"
              />
              <h1 className="text-xl font-semibold text-gray-900 hidden md:block">
                CATTLE Management System
              </h1>
            </div>
            
            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center space-x-3">
              <span className="text-sm text-gray-600 mr-2">Welcome, {user.name}</span>
              
              {/* Alerts Section */}
              <AlertsSection />
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowRegistrationModal(true)}
                className="flex items-center space-x-2 bg-white text-emerald-600 hover:bg-emerald-50 border-emerald-200"
              >
                <Plus className="w-4 h-4" />
                <span>Add Cow</span>
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowRfidAssignmentModal(true)}
                className="flex items-center space-x-2 bg-white text-emerald-600 hover:bg-emerald-50 border-emerald-200"
              >
                <Tag className="w-4 h-4" />
                <span>Assign RFID</span>
              </Button>
              
              <Button
                variant="outline"
                size="sm"
                onClick={logout}
                className="flex items-center space-x-2 bg-white text-red-600 hover:bg-red-50 border-red-200"
              >
                <LogOut className="w-4 h-4" />
                <span>Logout</span>
              </Button>
            </div>
            
            {/* Mobile Menu Button + Alerts */}
            <div className="flex md:hidden items-center space-x-2">
              <AlertsSection />
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="p-2"
              >
                {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
              </Button>
            </div>
          </div>
          
          {/* Mobile Dropdown Menu */}
          {mobileMenuOpen && (
            <div className="md:hidden border-t border-gray-200 py-4 space-y-2">
              <div className="px-4 py-2 text-sm text-gray-600 border-b border-gray-100">
                Welcome, <span className="font-medium">{user.name}</span>
              </div>
              
              <button
                onClick={() => {
                  setShowRegistrationModal(true);
                  setMobileMenuOpen(false);
                }}
                className="w-full flex items-center space-x-3 px-4 py-3 bg-white text-emerald-700 hover:bg-emerald-50 transition-colors"
              >
                <Plus className="w-5 h-5" />
                <span className="font-medium">Add Cow</span>
              </button>
              
              <button
                onClick={() => {
                  setShowRfidAssignmentModal(true);
                  setMobileMenuOpen(false);
                }}
                className="w-full flex items-center space-x-3 px-4 py-3 bg-white text-emerald-700 hover:bg-emerald-50 transition-colors"
              >
                <Tag className="w-5 h-5" />
                <span className="font-medium">Assign RFID</span>
              </button>
              
              <button
                onClick={() => {
                  logout();
                  setMobileMenuOpen(false);
                }}
                className="w-full flex items-center space-x-3 px-4 py-3 bg-white text-red-600 hover:bg-red-50 transition-colors border-t border-gray-100"
              >
                <LogOut className="w-5 h-5" />
                <span className="font-medium">Logout</span>
              </button>
            </div>
          )}
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

          {/* Choose Cow Section */}
          <ChooseCowSection 
            selectedCowName={selectedCowName}
            onCowSelect={handleCowSelect}
            onCattleUpdated={handleCattleRegistered}
            onSuccess={showToast}
            refreshTrigger={refreshCattle}
          />
          
          {/* Monitoring Section - Eating Session Summary */}
          <MonitoringSection selectedCowName={selectedCowName} />
          
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