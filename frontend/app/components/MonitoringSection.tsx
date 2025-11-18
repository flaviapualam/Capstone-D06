'use client';

import { Card, CardContent } from './ui/card';
import { Activity } from 'lucide-react';

export default function MonitoringSection() {
  // Simplified version - backend doesn't support status aggregation endpoint yet
  // TODO: Implement /farm/status endpoint in backend for real-time cattle monitoring

  return (
    <section className="space-y-6">
      <div className="flex items-center space-x-2">
        <Activity className="w-6 h-6 text-blue-600" />
        <h2 className="text-2xl font-bold">Cattle Monitoring</h2>
      </div>

      <Card>
        <CardContent className="py-12">
          <div className="text-center text-gray-600">
            <p className="text-lg mb-2">Status monitoring feature coming soon</p>
            <p className="text-sm">The backend /farm/status endpoint needs to be implemented to display real-time cattle health status.</p>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}