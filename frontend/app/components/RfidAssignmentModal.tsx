'use client';

import { useState, useEffect, ChangeEvent } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { cattleApi, rfidApi } from '@/lib/api';
import { Cattle } from '@/types';

interface RfidAssignmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (message: string) => void;
  onRfidAssigned?: () => void;
  refreshTrigger?: boolean;
}

export default function RfidAssignmentModal({
  isOpen,
  onClose,
  onSuccess,
  onRfidAssigned,
  refreshTrigger,
}: RfidAssignmentModalProps) {
  const [rfidId, setRfidId] = useState('');
  const [cowId, setCowId] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [cattleList, setCattleList] = useState<Cattle[]>([]);
  const [isLoadingData, setIsLoadingData] = useState(false);

  // Fetch cattle list
  useEffect(() => {
    if (isOpen) {
      fetchCattleList();
    }
  }, [isOpen, refreshTrigger]);

  const fetchCattleList = async () => {
    setIsLoadingData(true);
    try {
      const response = await cattleApi.getAll();
      if (response.success && response.data) {
        setCattleList(response.data);
      }
    } catch (error) {
      console.error('Error fetching cattle:', error);
      onSuccess?.('❌ Failed to load cattle list');
    } finally {
      setIsLoadingData(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!rfidId || !cowId) {
      onSuccess?.('❌ Please select both RFID and cattle');
      return;
    }

    setIsLoading(true);

    try {
      const response = await rfidApi.assign(rfidId, cowId);
      
      if (response.success) {
        const selectedCow = cattleList.find(c => c.cowId === cowId);
        onSuccess?.(`✅ RFID "${rfidId}" assigned to "${selectedCow?.name}" successfully!`);
        onRfidAssigned?.();
        setRfidId('');
        setCowId('');
        onClose();
      } else {
        onSuccess?.(`❌ Error: ${response.error || 'Failed to assign RFID'}`);
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error occurred';
      onSuccess?.(`❌ Error: ${errorMsg}`);
      console.error('Error assigning RFID:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Assign RFID to Cattle</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="rfid-id">RFID Tag ID *</Label>
            <Input
              id="rfid-id"
              type="text"
              value={rfidId}
              onChange={(e: ChangeEvent<HTMLInputElement>) => setRfidId(e.target.value)}
              placeholder="Enter RFID tag ID (e.g., RFID-001)"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Enter the RFID tag ID from your device
            </p>
          </div>

          <div>
            <Label htmlFor="cow-select">Select Cattle *</Label>
            <Select 
              id="cow-select"
              value={cowId} 
              onChange={(e) => setCowId(e.target.value)}
              disabled={isLoadingData}
              required
            >
              <SelectContent>
                <SelectValue placeholder={isLoadingData ? "Loading cattle..." : "Choose a cattle"} />
                {cattleList.map((cattle) => (
                  <SelectItem key={cattle.cowId} value={cattle.cowId}>
                    {cattle.name} {cattle.gender ? `(${cattle.gender})` : ''}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-gray-500 mt-1">
              Select the cattle to receive this RFID tag
            </p>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
            <p className="text-xs text-blue-800">
              <strong>Note:</strong> If the RFID was previously assigned to another cattle, 
              it will be automatically unassigned from the old cattle.
            </p>
          </div>

          <div className="flex justify-end space-x-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={isLoading}>
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading || isLoadingData}>
              {isLoading ? 'Assigning...' : 'Assign RFID'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
