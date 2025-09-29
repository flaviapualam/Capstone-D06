'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Activity, Weight } from 'lucide-react';
import { CattleStatus } from '@/types';
import { monitoringApi } from '@/lib/api';

export default function MonitoringSection() {
  const [cattleStatus, setCattleStatus] = useState<CattleStatus[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await monitoringApi.getStatus();
        if (response.success && response.data) {
          setCattleStatus(response.data);
        }
      } catch (error) {
        console.error('Error fetching monitoring data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000);

    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (health: string) => {
    switch (health) {
      case 'excellent':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'good':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'fair':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'poor':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  if (loading) {
    return (
      <section className="space-y-6">
        <div className="flex items-center space-x-2">
          <Activity className="w-6 h-6 text-blue-600" />
          <h2 className="text-2xl font-bold">Cattle Monitoring</h2>
        </div>
        <div className="text-center py-8">Loading monitoring data...</div>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <div className="flex items-center space-x-2">
        <Activity className="w-6 h-6 text-blue-600" />
        <h2 className="text-2xl font-bold">Cattle Monitoring</h2>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {cattleStatus.map((status: CattleStatus) => (
          <Card key={status.cowId} className="hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">{status.cattle.name}</CardTitle>
                <Badge className={getStatusColor(status.currentHealth)}>
                  {status.currentHealth}
                </Badge>
              </div>
              <p className="text-sm text-gray-600">ID: {status.cowId}</p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Activity className="w-4 h-4 text-blue-500" />
                  <span className="text-sm font-medium">Activity</span>
                </div>
                <span className="text-sm font-semibold">{status.lastReading.activityLevel}%</span>
              </div>
              
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Weight className="w-4 h-4 text-purple-500" />
                  <span className="text-sm font-medium">Weight</span>
                </div>
                <span className="text-sm font-semibold">{status.cattle.weight} kg</span>
              </div>
              
              <div className="pt-2 text-xs text-gray-500">
                Last update: {new Date(status.lastReading.timeGenerated).toLocaleTimeString()}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}
