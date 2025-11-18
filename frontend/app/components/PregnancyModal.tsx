'use client';

import { useState, ChangeEvent, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { pregnancyApi } from '@/lib/api';
import { Pencil, Trash2, Plus } from 'lucide-react';

interface PregnancyRecord {
  pregnancy_id: number;
  cow_id: string;
  time_start: string;
  expected_due_date?: string;
  time_end?: string;
}

interface PregnancyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (message: string) => void;
  onPregnancyRecorded?: () => void;
  cowId: string;
  cowName: string;
}

export default function PregnancyModal({
  isOpen,
  onClose,
  onSuccess,
  onPregnancyRecorded,
  cowId,
  cowName,
}: PregnancyModalProps) {
  const [pregnancies, setPregnancies] = useState<PregnancyRecord[]>([]);
  const [isLoadingList, setIsLoadingList] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingPregnancy, setEditingPregnancy] = useState<PregnancyRecord | null>(null);
  const [formData, setFormData] = useState({
    time_start: '',
    expected_due_date: '',
    time_end: '',
  });
  const [isLoading, setIsLoading] = useState(false);

  // Calculate status from time_end
  const getStatus = (pregnancy: PregnancyRecord): string => {
    if (!pregnancy.time_end) return 'ongoing';
    return 'completed';
  };

  // Fetch pregnancies when modal opens
  useEffect(() => {
    if (isOpen) {
      fetchPregnancies();
    } else {
      // Reset state when modal closes
      setShowForm(false);
      setEditingPregnancy(null);
      setFormData({
        time_start: '',
        expected_due_date: '',
        time_end: '',
      });
    }
  }, [isOpen, cowId]);

  const fetchPregnancies = async () => {
    setIsLoadingList(true);
    try {
      const response = await pregnancyApi.getAll(cowId);
      if (response.success && response.data) {
        setPregnancies(response.data);
      } else {
        console.error('Failed to fetch pregnancies:', response.error);
      }
    } catch (error) {
      console.error('Error fetching pregnancies:', error);
    } finally {
      setIsLoadingList(false);
    }
  };

  const handleAddNew = () => {
    setEditingPregnancy(null);
    setFormData({
      time_start: '',
      expected_due_date: '',
      time_end: '',
    });
    setShowForm(true);
  };

  const handleEdit = (pregnancy: PregnancyRecord) => {
    setEditingPregnancy(pregnancy);
    setFormData({
      time_start: pregnancy.time_start.split('T')[0],
      expected_due_date: pregnancy.expected_due_date ? pregnancy.expected_due_date.split('T')[0] : '',
      time_end: pregnancy.time_end ? pregnancy.time_end.split('T')[0] : '',
    });
    setShowForm(true);
  };

  const handleDelete = async (pregnancyId: number) => {
    if (!confirm('Are you sure you want to delete this pregnancy record?')) return;
    
    setIsLoading(true);
    try {
      const response = await pregnancyApi.delete(cowId, pregnancyId);
      if (response.success) {
        onSuccess?.(`✅ Pregnancy record deleted successfully!`);
        fetchPregnancies();
      } else {
        onSuccess?.(`❌ Error: ${response.error || 'Failed to delete pregnancy'}`);
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error occurred';
      onSuccess?.(`❌ Error: ${errorMsg}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      if (editingPregnancy) {
        // Update existing pregnancy - send time_end (can be empty to clear)
        const payload: any = {
          time_end: formData.time_end || null, // Send null to clear time_end
        };

        const response = await pregnancyApi.update(cowId, editingPregnancy.pregnancy_id, payload);
        
        if (response.success) {
          onSuccess?.(`✅ Pregnancy updated for "${cowName}" successfully!`);
          onPregnancyRecorded?.();
          await fetchPregnancies(); // AWAIT to ensure data is updated
          setShowForm(false);
          setEditingPregnancy(null);
          setFormData({
            time_start: '',
            expected_due_date: '',
            time_end: '',
          });
        } else {
          onSuccess?.(`❌ Error: ${response.error || 'Failed to update pregnancy'}`);
        }
      } else {
        // Create new pregnancy (only with start & expected_due_date)
        const payload: any = {
          time_start: formData.time_start,
        };

        if (formData.expected_due_date) {
          payload.expected_due_date = formData.expected_due_date;
        }

        const response = await pregnancyApi.create(cowId, payload);
        
        if (response.success) {
          // If user provided time_end, update the newly created pregnancy
          if (formData.time_end && response.data && response.data.pregnancy_id) {
            const updatePayload = {
              time_end: formData.time_end,
            };
            await pregnancyApi.update(cowId, response.data.pregnancy_id, updatePayload);
          }
          
          onSuccess?.(`✅ Pregnancy recorded for "${cowName}" successfully!`);
          onPregnancyRecorded?.();
          await fetchPregnancies(); // AWAIT to ensure data is updated
          setShowForm(false);
          setFormData({ // Clear form data after successful create
            time_start: '',
            expected_due_date: '',
            time_end: '',
          });
        } else {
          onSuccess?.(`❌ Error: ${response.error || 'Failed to record pregnancy'}`);
        }
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error occurred';
      onSuccess?.(`❌ Error: ${errorMsg}`);
      console.error('Error with pregnancy:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('id-ID', { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    });
  };

  const getStatusBadge = (pregnancy: PregnancyRecord) => {
    const status = getStatus(pregnancy);
    const statusColors: Record<string, string> = {
      ongoing: 'bg-blue-100 text-blue-800',
      completed: 'bg-green-100 text-green-800',
    };
    const statusLabels: Record<string, string> = {
      ongoing: 'Ongoing',
      completed: 'Completed',
    };
    
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-semibold ${statusColors[status]}`}>
        {statusLabels[status]}
      </span>
    );
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="w-[420px] max-w-[90vw] max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Pregnancy Records - {cowName}</DialogTitle>
        </DialogHeader>

        {!showForm ? (
          <div className="space-y-4">
            {/* List View */}
            <div className="flex justify-between items-center">
              <p className="text-sm text-gray-600">
                {pregnancies.length} pregnancy record(s)
              </p>
              <Button 
                onClick={handleAddNew}
                className="text-green-600 hover:bg-green-50 border-green-600"
                variant="outline"
                size="sm"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add New Pregnancy
              </Button>
            </div>

            {isLoadingList ? (
              <div className="text-center py-8 text-gray-500">
                Loading pregnancy records...
              </div>
            ) : pregnancies.length === 0 ? (
              <div className="text-center py-8 text-gray-500 border-2 border-dashed border-gray-300 rounded-lg">
                <p className="mb-2">No pregnancy records yet</p>
                <p className="text-xs">Click "Add New Pregnancy" to record one</p>
              </div>
            ) : (
              <div className="space-y-3">
                {pregnancies.map((pregnancy) => (
                  <div 
                    key={pregnancy.pregnancy_id}
                    className="border rounded-lg p-4 hover:shadow-md transition-shadow"
                  >
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="font-semibold">Pregnancy #{pregnancy.pregnancy_id}</h3>
                          {getStatusBadge(pregnancy)}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          onClick={() => handleEdit(pregnancy)}
                          variant="outline"
                          size="sm"
                          className="bg-white text-blue-600 hover:bg-blue-50 border-blue-200"
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          onClick={() => handleDelete(pregnancy.pregnancy_id)}
                          variant="outline"
                          size="sm"
                          className="bg-white text-red-600 hover:bg-red-50 border-red-200"
                          disabled={isLoading}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div>
                        <p className="text-gray-500 text-xs">Start Date</p>
                        <p className="font-medium">{formatDate(pregnancy.time_start)}</p>
                      </div>
                      <div>
                        <p className="text-gray-500 text-xs">Expected Due Date</p>
                        <p className="font-medium">{formatDate(pregnancy.expected_due_date || '')}</p>
                      </div>
                      {pregnancy.time_end && (
                        <div>
                          <p className="text-gray-500 text-xs">End Date</p>
                          <p className="font-medium">{formatDate(pregnancy.time_end)}</p>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="flex justify-end">
              <Button variant="outline" onClick={onClose} className="bg-white hover:bg-gray-100 text-gray-700">
                Close
              </Button>
            </div>
          </div>
        ) : (
          /* Form View */
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-semibold">
                {editingPregnancy ? 'Edit Pregnancy Record' : 'Add New Pregnancy'}
              </h3>
              <Button 
                type="button" 
                variant="outline" 
                size="sm"
                onClick={() => {
                  setShowForm(false);
                  setEditingPregnancy(null);
                }}
              >
                ← Back to List
              </Button>
            </div>

            {!editingPregnancy ? (
              <>
                <div>
                  <Label htmlFor="time_start">Pregnancy Start Date *</Label>
                  <Input
                    id="time_start"
                    name="time_start"
                    type="date"
                    value={formData.time_start}
                    onChange={handleChange}
                    required
                    className="bg-white"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    When did the pregnancy start?
                  </p>
                </div>

                <div>
                  <Label htmlFor="expected_due_date">Expected Due Date (Optional)</Label>
                  <Input
                    id="expected_due_date"
                    name="expected_due_date"
                    type="date"
                    value={formData.expected_due_date}
                    onChange={handleChange}
                    className="bg-white"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Estimated delivery date (typically 9 months from start)
                  </p>
                </div>

                <div>
                  <Label htmlFor="time_end">
                    End Date {formData.time_end ? '(Completed)' : '(Optional)'}
                  </Label>
                  <Input
                    id="time_end"
                    name="time_end"
                    type="date"
                    value={formData.time_end}
                    onChange={handleChange}
                    className="bg-white"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    {formData.time_end 
                      ? 'This pregnancy will be marked as completed'
                      : 'Leave empty if pregnancy is still ongoing'
                    }
                  </p>
                </div>
              </>
            ) : (
              <>
                <div className="bg-gray-50 p-3 rounded-md space-y-1">
                  <p className="text-sm"><strong>Start Date:</strong> {formatDate(editingPregnancy.time_start)}</p>
                  <p className="text-sm"><strong>Expected Due:</strong> {formatDate(editingPregnancy.expected_due_date || '')}</p>
                  <p className="text-sm">
                    <strong>Status:</strong> {formData.time_end ? 'Completed' : 'Ongoing'}
                  </p>
                </div>

                <div>
                  <Label htmlFor="time_end">
                    End Date {formData.time_end ? '(Completed)' : '(Optional)'}
                  </Label>
                  <Input
                    id="time_end"
                    name="time_end"
                    type="date"
                    value={formData.time_end}
                    onChange={handleChange}
                    className="bg-white"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    {formData.time_end 
                      ? 'This pregnancy is marked as completed. Clear the date to reopen.'
                      : 'Set end date to mark pregnancy as completed'
                    }
                  </p>
                </div>
              </>
            )}

            <div className="bg-pink-50 border border-pink-200 rounded-md p-3">
              <p className="text-xs text-pink-800">
                {editingPregnancy 
                  ? <><strong>Note:</strong> Setting an end date will automatically mark this pregnancy as "Completed".</>
                  : <><strong>Note:</strong> Pregnancy will be marked as "Ongoing" until you set an end date.</>
                }
              </p>
            </div>

            <div className="flex justify-end space-x-2">
              <Button 
                type="button" 
                variant="outline" 
                onClick={() => {
                  setShowForm(false);
                  setEditingPregnancy(null);
                }} 
                disabled={isLoading}
                className="bg-white hover:bg-gray-100 text-gray-700"
              >
                Cancel
              </Button>
              <Button 
                type="submit" 
                disabled={isLoading}
                className="bg-pink-600 hover:bg-pink-700 text-white"
              >
                {isLoading ? 'Saving...' : editingPregnancy ? 'Update Pregnancy' : 'Record Pregnancy'}
              </Button>
            </div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
