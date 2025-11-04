
'use client';

import { useState, ChangeEvent } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Cattle, CattleRegistrationData } from '@/types';
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
    age: '',
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
      const cattleData: CattleRegistrationData = {
        name: formData.name,
        age: parseInt(formData.age),
      };

      const response = await cattleApi.create(cattleData, user.farmerId);

      if (response.success && response.data) {
        onCattleRegistered(response.data);
        onSuccess?.(`✅ Cattle "${response.data.name}" added successfully!`);
        setFormData({
          name: '',
          age: '',
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
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Register New Cattle</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="cattle-name">Cattle Name</Label>
            <Input
              id="cattle-name"
              type="text"
              value={formData.name}
              onChange={(e: ChangeEvent<HTMLInputElement>) => handleInputChange('name', e.target.value)}
              placeholder="Enter cattle name"
              required
            />
          </div>

          <div>
            <Label htmlFor="age">Age (years)</Label>
            <Input
              id="age"
              type="number"
              value={formData.age}
              onChange={(e: ChangeEvent<HTMLInputElement>) => handleInputChange('age', e.target.value)}
              placeholder="Enter age"
              required
            />
          </div>

          <div className="flex justify-end space-x-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading}>
              {isLoading ? 'Registering...' : 'Register Cattle'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
