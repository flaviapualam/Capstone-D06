'use client';

import { useState, ChangeEvent } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Cattle } from '@/types';
import { cattleApi } from '@/lib/api';

interface CattleRegistrationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCattleRegistered: (cattle: Cattle) => void;
}

export default function CattleRegistrationModal({
  isOpen,
  onClose,
  onCattleRegistered,
}: CattleRegistrationModalProps) {
  const [formData, setFormData] = useState({
    name: '',
    breed: '',
    age: '',
    weight: '',
    notes: '',
    healthStatus: 'healthy' as const,
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
    setIsLoading(true);

    try {
      const cattleData = {
        name: formData.name,
        breed: formData.breed,
        age: parseInt(formData.age),
        weight: parseFloat(formData.weight),
        status: formData.healthStatus,
        notes: formData.notes,
      };

      const response = await cattleApi.create(cattleData);
      
      if (response.success && response.data) {
        onCattleRegistered(response.data);
        setFormData({
          name: '',
          breed: '',
          age: '',
          weight: '',
          notes: '',
          healthStatus: 'healthy' as const,
        });
        onClose();
      }
    } catch (error) {
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
          <div className="grid grid-cols-2 gap-4">
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
              <Label htmlFor="breed">Breed</Label>
              <Input
                id="breed"
                type="text"
                value={formData.breed}
                onChange={(e: ChangeEvent<HTMLInputElement>) => handleInputChange('breed', e.target.value)}
                placeholder="Enter breed"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
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
            <div>
              <Label htmlFor="health-status">Health Status</Label>
              <Select value={formData.healthStatus} onChange={(e: ChangeEvent<HTMLSelectElement>) => handleInputChange('healthStatus', e.target.value)}>
                <SelectValue placeholder="Select health status" />
                <SelectContent>
                  <SelectItem value="healthy">Healthy</SelectItem>
                  <SelectItem value="sick">Sick</SelectItem>
                  <SelectItem value="injured">Injured</SelectItem>
                  <SelectItem value="pregnant">Pregnant</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <Label htmlFor="weight">Weight (kg)</Label>
            <Input
              id="weight"
              type="number"
              step="0.1"
              value={formData.weight}
              onChange={(e: ChangeEvent<HTMLInputElement>) => handleInputChange('weight', e.target.value)}
              placeholder="Enter weight"
              required
            />
          </div>

          <div>
            <Label htmlFor="notes">Notes</Label>
            <Textarea
              id="notes"
              value={formData.notes}
              onChange={(e: ChangeEvent<HTMLTextAreaElement>) => handleInputChange('notes', e.target.value)}
              placeholder="Additional notes (optional)"
              rows={3}
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
