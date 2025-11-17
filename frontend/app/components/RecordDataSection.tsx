'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceDot } from 'recharts';
import { SensorReading } from '@/types';
import { monitoringApi } from '@/lib/api';
import { ChartNoAxesCombined, Thermometer, Weight } from 'lucide-react';

interface RecordDataSectionProps {
  selectedCowName?: string;
  selectedCowId?: string; // Add cow ID for API calls
}

interface ChartDataPoint {
  time: string;
  value: number;
  isAnomaly: boolean;
  timestamp: string;
}

type TimeRange = 'today' | '2days' | '7days' | '30days' | 'all';
type DataMode = 'historical' | 'live';

export default function RecordDataSection({ selectedCowName, selectedCowId }: RecordDataSectionProps) {
  const [sensorData, setSensorData] = useState<SensorReading[]>([]);
  const [allHistoricalData, setAllHistoricalData] = useState<SensorReading[]>([]); // Store all data for filtering
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<TimeRange>('today');
  const [dataMode, setDataMode] = useState<DataMode>('historical');

  useEffect(() => {
    const fetchSensorData = async () => {
      setLoading(true);
      try {
        // Need cow ID to fetch data
        if (!selectedCowId) {
          setSensorData([]);
          setAllHistoricalData([]);
          setLoading(false);
          return;
        }

        if (dataMode === 'historical') {
          // Fetch all historical data from /api/cow/{cow_id}/sensor_history
          const response = await monitoringApi.getSensorHistory(selectedCowId);
          if (response.success && response.data) {
            setAllHistoricalData(response.data); // Store all data
            setSensorData(response.data); // Will be filtered by getFilteredData()
          } else {
            console.error('Failed to fetch sensor history:', response.error);
            setAllHistoricalData([]);
            setSensorData([]);
          }
        } else {
          // Live/continuous mode - fetch from /api/streaming/cows/{cow_id}
          const response = await monitoringApi.getLiveData(selectedCowId);
          if (response.success && response.data) {
            setSensorData(response.data);
          } else {
            console.error('Failed to fetch live data:', response.error);
            setSensorData([]);
          }
        }
      } catch (error) {
        console.error('Error fetching sensor data:', error);
        setSensorData([]);
        setAllHistoricalData([]);
      } finally {
        setLoading(false);
      }
    };

    fetchSensorData();
    
    // Polling for live mode
    let interval: NodeJS.Timeout | null = null;
    if (dataMode === 'live' && selectedCowId) {
      interval = setInterval(fetchSensorData, 5000); // Poll every 5 seconds for live data
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [dataMode, selectedCowId]); // Re-fetch only when mode or cow changes (not timeRange!)

  // Filter data based on selected time range (only for historical mode)
  const getFilteredData = () => {
    // For live mode, always show all current data
    if (dataMode === 'live') {
      return sensorData;
    }
    
    // For historical mode, filter from allHistoricalData
    if (!allHistoricalData || allHistoricalData.length === 0) return [];
    
    const now = new Date();
    let startDate: Date;
    
    switch (timeRange) {
      case 'today':
        startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        break;
      case '2days':
        startDate = new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000);
        break;
      case '7days':
        startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        break;
      case '30days':
        startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        break;
      case 'all':
      default:
        return allHistoricalData;
    }
    
    return allHistoricalData.filter(reading => {
      const readingDate = new Date(reading.timeGenerated);
      return readingDate >= startDate;
    });
  };

  const getStatistics = (data: SensorReading[]) => {
    if (data.length === 0) return null;

    const temperatures = data.filter(d => d.temperature !== undefined).map(d => d.temperature as number);
    const feedWeights = data.filter(d => d.feedWeight !== undefined).map(d => d.feedWeight);

    const avgTemp = temperatures.length > 0 ? temperatures.reduce((a, b) => a + b, 0) / temperatures.length : 0;
    const minTemp = temperatures.length > 0 ? Math.min(...temperatures) : 0;
    const maxTemp = temperatures.length > 0 ? Math.max(...temperatures) : 0;

    const avgFeedWeight = feedWeights.length > 0 ? feedWeights.reduce((a, b) => a + b, 0) / feedWeights.length : 0;

    return {
      avgTemp: avgTemp.toFixed(1),
      minTemp: minTemp.toFixed(1),
      maxTemp: maxTemp.toFixed(1),
      avgFeedWeight: avgFeedWeight.toFixed(2),
    };
  };

  const prepareChartData = (dataType: 'feedWeight' | 'temperature'): ChartDataPoint[] => {
    const filteredData = getFilteredData();

    return filteredData
      .sort((a, b) => new Date(a.timeGenerated).getTime() - new Date(b.timeGenerated).getTime())
      .map((reading) => {
        let value: number;

        if (dataType === 'feedWeight') {
          value = reading.feedWeight ?? 0;
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
  const feedWeightData = prepareChartData('feedWeight');
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

          <div className="flex gap-4 items-end">
            {/* Data Mode Toggle */}
            <div className="flex flex-col">
              <label className="text-sm font-medium text-gray-700 mb-2">Data Mode</label>
              <select
                value={dataMode}
                onChange={(e) => setDataMode(e.target.value as DataMode)}
                className="px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent bg-white text-gray-900"
              >
                <option value="historical">Historical</option>
                <option value="live">Live Streaming</option>
              </select>
            </div>

            {/* Time Range Dropdown (only show in historical mode) */}
            {dataMode === 'historical' && (
              <div className="flex flex-col">
                <label className="text-sm font-medium text-gray-700 mb-2">Time Range</label>
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
            )}
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

        {/* Feed Weight Monitoring */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Weight className="w-5 h-5 text-orange-500" />
              <CardTitle>Feed Weight Trend</CardTitle>
            </div>
            <span className="text-sm font-normal text-gray-500">kg</span>
          </div>
        </CardHeader>
          <CardContent>
            {feedWeightData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={feedWeightData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="time"
                    tick={{ fontSize: 12 }}
                    interval={Math.max(0, Math.floor(feedWeightData.length / 6))}
                  />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#fff',
                      border: '1px solid #ccc',
                      borderRadius: '4px',
                    }}
                    formatter={(value: any) => `${value.toFixed(2)} kg`}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#f97316"
                    dot={false}
                    isAnimationActive={false}
                    name="Feed Weight"
                  />
                  {feedWeightData
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