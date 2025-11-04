'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Cattle } from '@/types';
import { cattleApi } from '@/lib/api';
import { useAuth } from '@/hooks/use-auth';
import { Pencil, Trash2 } from 'lucide-react';
import CattleEditModal from './CattleEditModal';

interface ChooseCowSectionProps {
  selectedCowName: string;
  onCowSelect: (cowName: string) => void;
  onCattleUpdated?: () => void;
  onSuccess?: (message: string) => void;
  refreshTrigger?: boolean;
}

export default function ChooseCowSection({ 
  selectedCowName, 
  onCowSelect, 
  onCattleUpdated,
  onSuccess,
  refreshTrigger 
}: ChooseCowSectionProps) {
  const [cattle, setCattle] = useState<Cattle[]>([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedCowForEdit, setSelectedCowForEdit] = useState<Cattle | null>(null);

  const fetchCattle = async () => {
    if (!user?.farmerId) {
      setLoading(false);
      return;
    }

    try {
      const response = await cattleApi.getAll(user.farmerId);
      if (response.success && response.data) {
        setCattle(response.data);
        // Auto-select first cattle if none selected
        if (!selectedCowName && response.data.length > 0) {
          onCowSelect(response.data[0].name);
        }
      }
    } catch (error) {
      console.error('Error fetching cattle:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCattle();
  }, [user?.farmerId, refreshTrigger]);

  const handleCattleUpdated = (updatedCattle: Cattle) => {
    setCattle(prev => 
      prev.map(c => c.name === updatedCattle.name ? updatedCattle : c)
    );
    setShowEditModal(false);
    setSelectedCowForEdit(null);
    onCattleUpdated?.();
  };

  const handleEditClick = (e: React.MouseEvent, cow: Cattle) => {
    e.stopPropagation();
    setSelectedCowForEdit(cow);
    setShowEditModal(true);
  };

  const handleDeleteClick = async (e: React.MouseEvent, cow: Cattle) => {
    e.stopPropagation();
    const confirmed = window.confirm(`Are you sure you want to delete "${cow.name}"?`);
    if (!confirmed) return;

    try {
      const response = await cattleApi.delete(cow.cowId);
      if (response.success) {
        setCattle(prev => prev.filter(c => c.cowId !== cow.cowId));
        onSuccess?.(`✅ Cattle "${cow.name}" deleted successfully!`);
        if (selectedCowName === cow.name) {
          onCowSelect('');
        }
      } else {
        onSuccess?.(`❌ Error: ${response.error || 'Failed to delete cattle'}`);
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error occurred';
      onSuccess?.(`❌ Error: ${errorMsg}`);
      console.error('Error deleting cattle:', error);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Choose Cow</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">Loading cattle...</div>
        </CardContent>
      </Card>
    );
  }

  if (cattle.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Choose Cow</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-gray-500">
            <p>No cattle found. Add one to get started!</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Choose Cow</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {cattle.map((cow) => (
              <div 
                key={cow.name}
                className={`rounded-lg border-2 transition-all cursor-pointer ${
                  selectedCowName === cow.name 
                    ? 'border-blue-500 ring-2 ring-blue-200 bg-blue-50' 
                    : 'border-gray-200 hover:border-gray-300 bg-white'
                }`}
                onClick={() => onCowSelect(cow.name)}
              >
                <div className="p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-semibold text-gray-900 text-lg">{cow.name}</h3>
                  </div>
                  
                  <div className="space-y-2 mb-4">
                    <p className="text-sm text-gray-600">
                      <span className="font-medium">Age:</span> {cow.age} years
                    </p>
                    <p className="text-sm text-gray-600">
                      <span className="font-medium">Farmer ID:</span> {cow.farmerId.substring(0, 8)}...
                    </p>
                  </div>

                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={(e) => handleEditClick(e, cow)}
                      className="flex-1 flex items-center justify-center gap-2"
                    >
                      <Pencil className="w-4 h-4" />
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={(e) => handleDeleteClick(e, cow)}
                      className="flex items-center justify-center gap-2 text-red-600 hover:text-red-700 border-red-200 hover:border-red-300"
                    >
                      <Trash2 className="w-4 h-4" />
                      Delete
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
          
          {selectedCowName && (
            <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-700">
                📍 Selected: <strong>{selectedCowName}</strong>
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <CattleEditModal
        isOpen={showEditModal}
        cattle={selectedCowForEdit}
        onClose={() => {
          setShowEditModal(false);
          setSelectedCowForEdit(null);
        }}
        onCattleUpdated={handleCattleUpdated}
        onSuccess={onSuccess}
      />
    </>
  );
}