'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceDot } from 'recharts';
import { SensorReading } from '@/types';
import { monitoringApi } from '@/lib/api';

interface RecordDataSectionProps {
  selectedCowId?: string;
}

interface ChartDataPoint {
  time: string;
  value: number;
  isAnomaly: boolean;
  timestamp: string;
}

export default function RecordDataSection({ selectedCowId }: RecordDataSectionProps) {
  const [sensorData, setSensorData] = useState<SensorReading[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSensorData = async () => {
      try {
        const response = await monitoringApi.getSensorData();
        if (response.success && response.data) {
          setSensorData(response.data);
        }
      } catch (error) {
        console.error('Error fetching sensor data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchSensorData();
    const interval = setInterval(fetchSensorData, 30000);

    return () => clearInterval(interval);
  }, [selectedCowId]);

  const prepareChartData = (dataType: 'eatSpeed' | 'eatDuration'): ChartDataPoint[] => {
    let filteredData = sensorData.filter(reading => {
      const matchesCattle = selectedCowId ? reading.cowId === selectedCowId : true;
      return matchesCattle;
    });

    // Sort by timeGenerated and get last 20 readings
    filteredData = filteredData
      .sort((a, b) => new Date(a.timeGenerated).getTime() - new Date(b.timeGenerated).getTime())
      .slice(-20);

    return filteredData.map(reading => {
      let value: number;
      let isAnomaly = reading.isAnomaly || false;

      if (dataType === 'eatSpeed') {
        value = reading.eatSpeed;
      } else {
        value = reading.eatDuration;
      }

      return {
        time: new Date(reading.timeGenerated).toLocaleTimeString('en-US', { 
          hour: '2-digit', 
          minute: '2-digit' 
        }),
        value,
        isAnomaly,
        timestamp: reading.timeGenerated
      };
    });
  };

  const eatSpeedData = prepareChartData('eatSpeed');
  const eatDurationData = prepareChartData('eatDuration');

  if (loading) {
    return (
      <section className="space-y-6">
        <h2 className="text-2xl font-bold text-gray-900">Record Data</h2>
        <div className="grid md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Loading...</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80 bg-gray-100 animate-pulse rounded"></div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Loading...</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80 bg-gray-100 animate-pulse rounded"></div>
            </CardContent>
          </Card>
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Record Data - Eating Patterns</h2>
        {selectedCowId && (
          <span className="text-sm text-gray-600 bg-gray-100 px-3 py-1 rounded-full">
            Cattle ID: {selectedCowId}
          </span>
        )}
      </div>
      <div className="grid md:grid-cols-2 gap-6">
        {/* Eating Speed Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              Eating Speed
              <span className="text-sm font-normal text-gray-500">kg/hour</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={eatSpeedData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="time" 
                  fontSize={12}
                  tick={{ fill: '#6b7280' }}
                />
                <YAxis 
                  domain={['dataMin - 1', 'dataMax + 1']}
                  fontSize={12}
                  tick={{ fill: '#6b7280' }}
                />
                <Tooltip 
                  labelFormatter={(label) => `Time: ${label}`}
                  formatter={(value: number) => [`${value} kg/hour`, 'Eating Speed']}
                />
                <Line 
                  type="monotone" 
                  dataKey="value" 
                  stroke="#22c55e" 
                  strokeWidth={2}
                  dot={false}
                />
                {eatSpeedData.map((point, index) => 
                  point.isAnomaly ? (
                    <ReferenceDot
                      key={index}
                      x={point.time}
                      y={point.value}
                      r={4}
                      fill="#ef4444"
                      stroke="#dc2626"
                      strokeWidth={2}
                    />
                  ) : null
                )}
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Eating Duration Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              Eating Duration
              <span className="text-sm font-normal text-gray-500">minutes</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={eatDurationData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="time" 
                  fontSize={12}
                  tick={{ fill: '#6b7280' }}
                />
                <YAxis 
                  domain={['dataMin - 5', 'dataMax + 5']}
                  fontSize={12}
                  tick={{ fill: '#6b7280' }}
                />
                <Tooltip 
                  labelFormatter={(label) => `Time: ${label}`}
                  formatter={(value: number) => [`${value} minutes`, 'Eating Duration']}
                />
                <Line 
                  type="monotone" 
                  dataKey="value" 
                  stroke="#3b82f6" 
                  strokeWidth={2}
                  dot={false}
                />
                {eatDurationData.map((point, index) => 
                  point.isAnomaly ? (
                    <ReferenceDot
                      key={index}
                      x={point.time}
                      y={point.value}
                      r={4}
                      fill="#ef4444"
                      stroke="#dc2626"
                      strokeWidth={2}
                    />
                  ) : null
                )}
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </section>
  );
}