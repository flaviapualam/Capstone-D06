
'use client';

import { useState, ChangeEvent } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Cattle } from '@/types';
import { cattleApi } from '@/lib/api';
import { useAuth } from '@/hooks/use-auth';

interface CattleRegistrationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCattleRegistered: (cattle: Cattle) => void;
  onSuccess?: (message: string) => void;
}

export default function CattleRegistrationModal({
  isOpen,
  onClose,
  onCattleRegistered,
  onSuccess,
}: CattleRegistrationModalProps) {
  const { user } = useAuth();
  const [formData, setFormData] = useState({
    name: '',
    date_of_birth: '',
    gender: '' as 'MALE' | 'FEMALE' | '',
  });
  const [isLoading, setIsLoading] = useState(false);

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!user?.farmerId) {
      console.error('No farmer ID available');
      return;
    }

    setIsLoading(true);

    try {
      const cattleData: any = {
        name: formData.name,
      };

      // Add optional fields only if provided
      if (formData.date_of_birth) {
        cattleData.date_of_birth = formData.date_of_birth;
      }
      if (formData.gender) {
        cattleData.gender = formData.gender;
      }

      const response = await cattleApi.create(cattleData);

      if (response.success && response.data) {
        onCattleRegistered(response.data);
        onSuccess?.(`✅ Cattle "${response.data.name}" added successfully!`);
        setFormData({
          name: '',
          date_of_birth: '',
          gender: '',
        });
        onClose();
      } else {
        onSuccess?.(`❌ Error: ${response.error || 'Failed to add cattle'}`);
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error occurred';
      onSuccess?.(`❌ Error: ${errorMsg}`);
      console.error('Error registering cattle:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="w-[420px] max-w-[90vw] max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Register New Cattle</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="cattle-name">Cattle Name *</Label>
            <Input
              id="cattle-name"
              type="text"
              value={formData.name}
              onChange={(e: ChangeEvent<HTMLInputElement>) => handleInputChange('name', e.target.value)}
              placeholder="Enter cattle name"
              required
              className="bg-white"
            />
          </div>

          <div>
            <Label htmlFor="date_of_birth">Date of Birth</Label>
            <Input
              id="date_of_birth"
              type="date"
              value={formData.date_of_birth}
              onChange={(e: ChangeEvent<HTMLInputElement>) => handleInputChange('date_of_birth', e.target.value)}
              placeholder="Select birth date"
              className="bg-white"
            />
            <p className="text-xs text-gray-500 mt-1">Optional - Leave empty if unknown</p>
          </div>

          <div>
            <Label htmlFor="gender">Gender</Label>
            <select
              id="gender"
              value={formData.gender}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => handleInputChange('gender', e.target.value)}
              className="w-full px-3 py-2 bg-white border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900"
            >
              <option value="">Select gender (optional)</option>
              <option value="FEMALE">Female</option>
              <option value="MALE">Male</option>
            </select>
            <p className="text-xs text-gray-500 mt-1">Optional - Leave empty if unknown</p>
          </div>

          <div className="flex justify-end space-x-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={isLoading} className="bg-white hover:bg-gray-100 text-gray-700">
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading} className="bg-blue-600 hover:bg-blue-700 text-white">
              {isLoading ? 'Registering...' : 'Register Cattle'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
