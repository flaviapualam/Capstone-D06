'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceDot } from 'recharts';
import { SensorReading } from '@/types';
import { monitoringApi } from '@/lib/api';
import { ChartNoAxesCombined, Thermometer, Gauge } from 'lucide-react';

interface RecordDataSectionProps {
  selectedCowName?: string;
}

interface ChartDataPoint {
  time: string;
  value: number;
  isAnomaly: boolean;
  timestamp: string;
}

type TimeRange = 'today' | '2days' | '7days' | '30days' | 'all';

export default function RecordDataSection({ selectedCowName }: RecordDataSectionProps) {
  const [sensorData, setSensorData] = useState<SensorReading[]>([]);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<TimeRange>('today');

  useEffect(() => {
    const fetchSensorData = async () => {
      try {
        // TODO: Backend sensor-data endpoint not implemented yet
        // Uncomment when /api/sensor-data or /api/output-sensor is available
        // const response = await monitoringApi.getSensorData();
        // if (response.success && response.data) {
        //   setSensorData(response.data);
        // }
        
        // For now, set empty data to avoid 404 errors
        setSensorData([]);
      } catch (error) {
        console.error('Error fetching sensor data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchSensorData();
    // Disable polling until backend endpoint is ready
    // const interval = setInterval(fetchSensorData, 30000);
    // return () => clearInterval(interval);
  }, []);

  const getFilteredData = (): SensorReading[] => {
    const now = new Date();
    let startDate = new Date();

    switch (timeRange) {
      case 'today':
        startDate.setHours(0, 0, 0, 0);
        break;
      case '2days':
        startDate.setDate(startDate.getDate() - 2);
        break;
      case '7days':
        startDate.setDate(startDate.getDate() - 7);
        break;
      case '30days':
        startDate.setDate(startDate.getDate() - 30);
        break;
      case 'all':
        return sensorData;
    }

    return sensorData.filter((reading) => {
      const readingDate = new Date(reading.timeGenerated);
      return readingDate >= startDate && readingDate <= now;
    });
  };

  const getStatistics = (data: SensorReading[]) => {
    if (data.length === 0) return null;

    const temperatures = data.filter(d => d.temperature !== undefined).map(d => d.temperature as number);
    const eatSpeeds = data.filter(d => d.eatSpeed !== undefined).map(d => d.eatSpeed);

    const avgTemp = temperatures.length > 0 ? temperatures.reduce((a, b) => a + b, 0) / temperatures.length : 0;
    const minTemp = temperatures.length > 0 ? Math.min(...temperatures) : 0;
    const maxTemp = temperatures.length > 0 ? Math.max(...temperatures) : 0;

    const avgEatSpeed = eatSpeeds.length > 0 ? eatSpeeds.reduce((a, b) => a + b, 0) / eatSpeeds.length : 0;

    return {
      avgTemp: avgTemp.toFixed(1),
      minTemp: minTemp.toFixed(1),
      maxTemp: maxTemp.toFixed(1),
      avgEatSpeed: avgEatSpeed.toFixed(2),
    };
  };

  const prepareChartData = (dataType: 'eatSpeed' | 'temperature'): ChartDataPoint[] => {
    const filteredData = getFilteredData();

    return filteredData
      .sort((a, b) => new Date(a.timeGenerated).getTime() - new Date(b.timeGenerated).getTime())
      .map((reading) => {
        let value: number;

        if (dataType === 'eatSpeed') {
          value = reading.eatSpeed ?? 0;
        } else if (dataType === 'temperature') {
          value = reading.temperature ?? 0;
        } else {
          value = 0;
        }

        return {
          time: new Date(reading.timeGenerated).toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
          }),
          value,
          isAnomaly: reading.isAnomaly || false,
          timestamp: reading.timeGenerated,
        };
      });
  };

  const filteredData = getFilteredData();
  const eatSpeedData = prepareChartData('eatSpeed');
  const temperatureData = prepareChartData('temperature');

  const timeRangeOptions: { label: string; value: TimeRange }[] = [
    { label: 'Today', value: 'today' },
    { label: 'Last 2 Days', value: '2days' },
    { label: 'Last 7 Days', value: '7days' },
    { label: 'Last 30 Days', value: '30days' },
    { label: 'All Data', value: 'all' },
  ];

  if (loading) {
    return (
      <div className="grid gap-6">
        {Array.from({ length: 2 }).map((_, i) => (
          <Card key={i}>
            <CardHeader>
              <CardTitle>Loading...</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80 bg-gray-100 animate-pulse rounded"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <section className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="flex items-center space-x-2">
              <ChartNoAxesCombined className="w-7 h-7 text-purple-600" />
              <h2 className="text-2xl font-bold text-gray-900">Record Data</h2>
            </div>
            <p className="text-sm text-gray-600 mt-1">Track eating patterns</p>
          </div>

          {/* Time Range Dropdown */}
          <div className="flex flex-col items-end">
            <label className="text-sm font-medium text-gray-700 mb-2">Select Time Range</label>
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value as TimeRange)}
              className="px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white text-gray-900"
            >
              <option value="today">Today</option>
              <option value="2days">Last 2 Days</option>
              <option value="7days">Last 7 Days</option>
              <option value="30days">Last 30 Days</option>
              <option value="all">All Data</option>
            </select>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Temperature Monitoring */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Thermometer className="w-5 h-5 text-red-500" />
              <CardTitle>Temperature Trend</CardTitle>
            </div>
            <span className="text-sm font-normal text-gray-500">°C</span>
          </div>
        </CardHeader>
        <CardContent>
            {temperatureData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={temperatureData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="time"
                    tick={{ fontSize: 12 }}
                    interval={Math.max(0, Math.floor(temperatureData.length / 6))}
                  />
                  <YAxis domain={[36, 41]} tick={{ fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #ccc',
                      borderRadius: '4px',
                    }}
                    formatter={(value: any) => `${value.toFixed(1)}°C`}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#ef4444"
                    dot={false}
                    isAnimationActive={false}
                    name="Temperature"
                  />
                  {temperatureData
                    .filter((d) => d.isAnomaly)
                    .map((point, idx) => (
                      <ReferenceDot
                        key={idx}
                        x={point.time}
                        y={point.value}
                        r={5}
                        fill="#ff0000"
                        fillOpacity={0.7}
                      />
                    ))}
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-80 flex items-center justify-center text-gray-500">
                No data available for selected period
              </div>
            )}
          </CardContent>
        </Card>

        {/* Eating Speed Monitoring */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Gauge className="w-5 h-5 text-red-500" />
              <CardTitle>Eating Speed Trend</CardTitle>
            </div>
            <span className="text-sm font-normal text-gray-500">kg/hour</span>
          </div>
        </CardHeader>
          <CardContent>
            {eatSpeedData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={eatSpeedData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="time"
                    tick={{ fontSize: 12 }}
                    interval={Math.max(0, Math.floor(eatSpeedData.length / 6))}
                  />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #ccc',
                      borderRadius: '4px',
                    }}
                    formatter={(value: any) => value.toFixed(2)}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#a855f7"
                    dot={false}
                    isAnimationActive={false}
                    name="Eating Speed"
                  />
                  {eatSpeedData
                    .filter((d) => d.isAnomaly)
                    .map((point, idx) => (
                      <ReferenceDot
                        key={idx}
                        x={point.time}
                        y={point.value}
                        r={5}
                        fill="#ff0000"
                        fillOpacity={0.7}
                      />
                    ))}
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-80 flex items-center justify-center text-gray-500">
                No data available for selected period
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </section>
  );
}