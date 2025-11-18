'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceDot } from 'recharts';
import { SensorReading } from '@/types';
import { monitoringApi } from '@/lib/api';
import { ChartNoAxesCombined, Thermometer, Weight, Wifi, WifiOff } from 'lucide-react';

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
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<TimeRange>('today');
  const [dataMode, setDataMode] = useState<DataMode>('historical');
  const [isLiveConnected, setIsLiveConnected] = useState(false);
  const [liveDataCount, setLiveDataCount] = useState(0);
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected'>('disconnected');
  const [errorMessage, setErrorMessage] = useState<string>('');

  useEffect(() => {
    const fetchSensorData = async () => {
      setLoading(true);
      try {
        // Need cow ID to fetch data
        if (!selectedCowId) {
          console.log('No cow selected, selectedCowId:', selectedCowId);
          setSensorData([]);
          setLoading(false);
          return;
        }

        if (dataMode === 'historical') {
          // Historical mode - fetch once
          console.log(`Fetching historical data for cow ${selectedCowId} with timeRange: ${timeRange}`);
          
          const response = await monitoringApi.getSensorHistory(selectedCowId, timeRange);
          console.log('Historical data response:', response);
          
          if (response.success && response.data) {
            setSensorData(response.data);
            console.log(`Loaded ${response.data.length} historical records`);
          } else {
            console.error('Failed to fetch sensor history:', response.error);
            setSensorData([]);
          }
          setLoading(false);
        } else {
          // Live mode - use SSE streaming
          console.log(`Starting live stream for cow ${selectedCowId}`);
          setConnectionStatus('connecting');
          setErrorMessage('');
          
          // Initial load - get last 24h of data
          const historyResponse = await monitoringApi.getSensorHistory(selectedCowId, 'today');
          if (historyResponse.success && historyResponse.data) {
            setSensorData(historyResponse.data);
            console.log(`Loaded ${historyResponse.data.length} initial records for live mode`);
          }
          setLoading(false);
          
          // Connect to SSE stream
          const eventSource = monitoringApi.createLiveStream(
            selectedCowId,
            (newReading) => {
              console.log('New live data received:', newReading);
              setIsLiveConnected(true);
              setConnectionStatus('connected');
              setLiveDataCount(prev => prev + 1);
              setErrorMessage('');
              
              // Append new reading to existing data
              setSensorData(prevData => {
                const updated = [...prevData, newReading];
                // Keep only last 1000 points to avoid memory issues
                return updated.slice(-1000);
              });
            },
            (error) => {
              console.error('Live stream error:', error);
              setIsLiveConnected(false);
              setConnectionStatus('disconnected');
              setErrorMessage(error);
            },
            () => {
              // onOpen callback
              console.log('✅ SSE connection opened');
              setConnectionStatus('connecting'); // Still connecting until we receive first data
            }
          );
          
          // Cleanup function to close EventSource
          return () => {
            console.log('Closing SSE connection');
            eventSource.close();
            setIsLiveConnected(false);
            setConnectionStatus('disconnected');
            setLiveDataCount(0);
          };
        }
      } catch (error) {
        console.error('Error fetching sensor data:', error);
        setSensorData([]);
        setLoading(false);
      }
    };

    fetchSensorData();
  }, [dataMode, timeRange, selectedCowId]); // Re-fetch when mode, time range, or cow changes

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
    return sensorData
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

  // Calculate dynamic Y-axis domain for temperature chart
  const getTemperatureDomain = () => {
    if (temperatureData.length === 0) return [36, 41];
    
    const temps = temperatureData.map(d => d.value).filter(v => v > 0);
    if (temps.length === 0) return [36, 41];
    
    const minTemp = Math.min(...temps);
    const maxTemp = Math.max(...temps);
    
    // Add small padding (0.5°C) above and below for better visualization
    const padding = 0.5;
    return [
      Math.max(0, Math.floor(minTemp - padding)),
      Math.ceil(maxTemp + padding)
    ];
  };

  const feedWeightData = prepareChartData('feedWeight');
  const temperatureData = prepareChartData('temperature');

  // Note: Backend max is 24 hours, so all options fetch 24h data
  const timeRangeOptions: { label: string; value: TimeRange }[] = [
    { label: 'Last 24 Hours', value: 'today' },
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
            <p className="text-sm text-gray-600 mt-1">
              Track eating patterns {selectedCowName && `for ${selectedCowName}`}
            </p>
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
                <option value="historical">Historical (Last 24h)</option>
                <option value="live">Live Streaming (Real-time)</option>
              </select>
            </div>

            {/* Live Status Indicator */}
            {dataMode === 'live' && (
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg border border-gray-200">
                  {connectionStatus === 'connected' && isLiveConnected ? (
                    <>
                      <Wifi className="w-4 h-4 text-green-500 animate-pulse" />
                      <span className="text-sm font-medium text-green-700">
                        Live ({liveDataCount} updates)
                      </span>
                    </>
                  ) : connectionStatus === 'connecting' ? (
                    <>
                      <WifiOff className="w-4 h-4 text-blue-500 animate-pulse" />
                      <span className="text-sm font-medium text-blue-700">
                        Waiting for data...
                      </span>
                    </>
                  ) : (
                    <>
                      <WifiOff className="w-4 h-4 text-red-400" />
                      <span className="text-sm font-medium text-red-500">
                        Connection Failed
                      </span>
                    </>
                  )}
                </div>
                {errorMessage && (
                  <span className="text-xs text-red-500 ml-1">{errorMessage}</span>
                )}
                {connectionStatus === 'connecting' && !errorMessage && (
                  <span className="text-xs text-blue-600 ml-1">
                    ℹ️ Connection established. Waiting for sensor activity...
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
        
        {/* Info Banner for Live Mode */}
        {dataMode === 'live' && !selectedCowId && (
          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-start gap-2">
              <div className="text-blue-600 text-sm">
                <p className="font-medium">ℹ️ Please select a cow first</p>
                <p className="text-xs text-blue-500 mt-1">
                  Live streaming requires a selected cow to monitor sensor activity
                </p>
              </div>
            </div>
          </div>
        )}
        
        {dataMode === 'live' && selectedCowId && connectionStatus === 'connecting' && (
          <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <div className="flex items-start gap-2">
              <div className="text-amber-700 text-sm">
                <p className="font-medium">💡 Waiting for sensor activity</p>
                <p className="text-xs text-amber-600 mt-1">
                  Live data will appear when the cow starts eating. The system is actively monitoring...
                </p>
              </div>
            </div>
          </div>
        )}
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
                  <YAxis domain={getTemperatureDomain()} tick={{ fontSize: 12 }} />
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
                    isAnimationActive={dataMode === 'historical'} // Disable animation in live mode
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
              <div className="h-80 flex flex-col items-center justify-center text-gray-500 space-y-3">
                <div className="text-center">
                  {dataMode === 'live' ? (
                    <>
                      <Thermometer className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                      <p className="text-base font-medium">⏳ Waiting for live sensor data...</p>
                      <p className="text-sm text-gray-400 mt-2">
                        Temperature data will appear when cow starts eating activity
                      </p>
                    </>
                  ) : (
                    <p className="text-base">No data available for selected period</p>
                  )}
                </div>
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
                    isAnimationActive={dataMode === 'historical'}
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
              <div className="h-80 flex flex-col items-center justify-center text-gray-500 space-y-3">
                <div className="text-center">
                  {dataMode === 'live' ? (
                    <>
                      <Weight className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                      <p className="text-base font-medium">⏳ Waiting for live sensor data...</p>
                      <p className="text-sm text-gray-400 mt-2">
                        Feed weight data will appear when cow starts eating activity
                      </p>
                    </>
                  ) : (
                    <p className="text-base">No data available for selected period</p>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </section>
  );
}