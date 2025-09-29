'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Cattle } from '@/types';
import { cattleApi } from '@/lib/api';

interface ChooseCowSectionProps {
  selectedCowId: string;
  onCowSelect: (cowId: string) => void;
}

export default function ChooseCowSection({ selectedCowId, onCowSelect }: ChooseCowSectionProps) {
  const [cattle, setCattle] = useState<Cattle[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCattle = async () => {
      try {
        const response = await cattleApi.getAll();
        if (response.success && response.data) {
          setCattle(response.data);
          // Auto-select first cattle if none selected
          if (!selectedCowId && response.data.length > 0) {
            onCowSelect(response.data[0].cowId);
          }
        }
      } catch (error) {
        console.error('Error fetching cattle:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchCattle();
  }, [selectedCowId, onCowSelect]);

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

  return (
    <Card>
      <CardHeader>
        <CardTitle>Choose Cow</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {cattle.map((cow) => (
            <div 
              key={cow.cowId}
              className={`cursor-pointer rounded-lg overflow-hidden border-2 transition-all ${
                selectedCowId === cow.cowId 
                  ? 'border-blue-500 ring-2 ring-blue-200' 
                  : 'border-gray-200 hover:border-gray-300'
              }`}
              onClick={() => onCowSelect(cow.cowId)}
            >
              {cow.image && (
                <img 
                  src={cow.image}
                  alt={cow.name}
                  className="w-full h-32 object-cover"
                  onError={(e) => {
                    e.currentTarget.style.display = 'none';
                  }}
                />
              )}
              <div className="p-4 bg-white">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-medium text-gray-900">{cow.name}</h3>
                  <Badge variant={cow.status === 'healthy' ? 'default' : 'destructive'}>
                    {cow.status}
                  </Badge>
                </div>
                <p className="text-sm text-gray-600 mb-1">{cow.cowId}</p>
                <p className="text-xs text-gray-500">
                  {cow.breed} • {cow.age} years • {cow.weight}kg
                </p>
              </div>
            </div>
          ))}
        </div>
        
        {selectedCowId && (
          <div className="mt-4 p-4 bg-blue-50 rounded-lg">
            <p className="text-sm text-blue-700">
              Selected: <strong>{cattle.find(c => c.cowId === selectedCowId)?.name}</strong> ({selectedCowId})
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}