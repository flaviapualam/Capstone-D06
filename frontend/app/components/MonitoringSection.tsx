'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { UtensilsCrossed, Clock, Weight, Thermometer, ChevronDown, ChevronUp, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';

interface MonitoringSectionProps {
  selectedCowId?: string;
  selectedCowName?: string;
  onShowToast?: (message: string, type: 'success' | 'error') => void;
}

type ViewMode = 'daily' | 'weekly';

export default function MonitoringSection({ selectedCowId, selectedCowName, onShowToast }: MonitoringSectionProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('daily');
  const [showDetails, setShowDetails] = useState(false);
  const [loading, setLoading] = useState(true);
  const [eatingData, setEatingData] = useState<any>(null);

  // Fetch eating data from API
  useEffect(() => {
    const fetchEatingData = async () => {
      if (!selectedCowId) {
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        const response = await api.eatingSession.getWeeklySummary(selectedCowId, 2);
        if (response.success && response.data) {
          setEatingData(response.data);
        } else {
          console.error('Failed to fetch eating data:', response.error);
          onShowToast?.('Failed to load eating session data', 'error');
        }
      } catch (error) {
        console.error('Error fetching eating data:', error);
        onShowToast?.('Error loading eating data', 'error');
      } finally {
        setLoading(false);
      }
    };

    fetchEatingData();
  }, [selectedCowId]);

  // Helper functions
  const formatDuration = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    if (hours > 0) {
      return `${hours}:${mins.toString().padStart(2, '0')}`;
    }
    return `${mins}:00`;
  };

  const formatWeight = (grams: number): string => {
    return `${(grams / 1000).toFixed(2)} kg`;
  };

  const formatSpeed = (gramsPerSecond: number): string => {
    return `${gramsPerSecond.toFixed(2)} g/s`;
  };

  const formatSessionTime = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
  };

  // Loading state
  if (loading) {
    return (
      <section className="space-y-6">
        <div className="flex items-center space-x-2">
          <UtensilsCrossed className="w-6 h-6 text-blue-600" />
          <h2 className="text-2xl font-bold">Eating Session Summary</h2>
        </div>
        <Card>
          <CardContent className="py-12">
            <div className="flex items-center justify-center">
              <Loader2 className="w-12 h-12 animate-spin text-blue-600" />
            </div>
          </CardContent>
        </Card>
      </section>
    );
  }

  // No cow selected or no data
  if (!selectedCowId || !eatingData || !eatingData.current_week) {
    return (
      <section className="space-y-6">
        <div className="flex items-center space-x-2">
          <UtensilsCrossed className="w-6 h-6 text-blue-600" />
          <h2 className="text-2xl font-bold">Eating Session Summary</h2>
        </div>

        <Card>
          <CardContent className="py-12">
            <div className="text-center text-gray-600">
              <p className="text-lg mb-2">No eating data available</p>
              <p className="text-sm">Please select a cow to view eating session summary</p>
            </div>
          </CardContent>
        </Card>
      </section>
    );
  }

  // Prepare data for display
  const currentWeek = eatingData.current_week;
  const todayData = currentWeek.daily_summaries?.[currentWeek.daily_summaries.length - 1];
  const todaySessions = todayData?.sessions || [];
  const currentData = viewMode === 'weekly' ? currentWeek : todayData;

  return (
    <section className="space-y-6">
      {/* Header with view mode toggle */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <UtensilsCrossed className="w-6 h-6 text-blue-600" />
          <h2 className="text-2xl font-bold">Eating Session Summary</h2>
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={() => setViewMode('daily')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              viewMode === 'daily'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200'
            }`}
          >
            Daily
          </button>
          <button
            onClick={() => setViewMode('weekly')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              viewMode === 'weekly'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100 border border-gray-200'
            }`}
          >
            Weekly
          </button>
        </div>
      </div>

      {/* Summary Card - White theme like other components */}
      <Card className="border border-gray-200 shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg font-semibold text-gray-900">
            {viewMode === 'daily' ? "Today's Eating Activity" : "This Week's Eating Activity"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {/* Total Duration */}
            <div className="bg-blue-50 rounded-lg p-4 border border-blue-100">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="w-4 h-4 text-blue-600" />
                <div className="text-xs font-medium text-blue-600 uppercase">Total Time</div>
              </div>
              <div className="text-2xl font-bold text-gray-900">
                {formatDuration(currentData?.total_eat_duration || 0)}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {currentData?.total_sessions || 0} session{(currentData?.total_sessions || 0) > 1 ? 's' : ''}
              </div>
            </div>

            {/* Sessions */}
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
              <div className="flex items-center gap-2 mb-2">
                <UtensilsCrossed className="w-4 h-4 text-gray-600" />
                <div className="text-xs font-medium text-gray-600 uppercase">Sessions</div>
              </div>
              <div className="text-2xl font-bold text-gray-900">
                {currentData?.total_sessions || 0}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                eating times
              </div>
            </div>
            
            {/* Feed Weight */}
            <div className="bg-amber-50 rounded-lg p-4 border border-amber-100">
              <div className="flex items-center gap-2 mb-2">
                <Weight className="w-4 h-4 text-amber-600" />
                <div className="text-xs font-medium text-amber-600 uppercase">Feed Weight</div>
              </div>
              <div className="text-2xl font-bold text-gray-900">
                {formatWeight(currentData?.total_feed_weight || 0)}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                consumed
              </div>
            </div>

            {/* Avg Temperature */}
            <div className="bg-red-50 rounded-lg p-4 border border-red-100">
              <div className="flex items-center gap-2 mb-2">
                <Thermometer className="w-4 h-4 text-red-600" />
                <div className="text-xs font-medium text-red-600 uppercase">Avg Temp</div>
              </div>
              <div className="text-2xl font-bold text-gray-900">
                {currentData?.avg_temperature?.toFixed(1) || 'N/A'}°C
              </div>
              <div className="text-xs text-gray-500 mt-1">
                body temp
              </div>
            </div>
          </div>

          {/* Session Details Dropdown */}
          <div className="border-t border-gray-200 pt-4">
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <span className="font-medium text-gray-900">
                View {viewMode === 'daily' ? 'Session' : 'Daily'} Details
              </span>
              {showDetails ? (
                <ChevronUp className="w-5 h-5 text-gray-500" />
              ) : (
                <ChevronDown className="w-5 h-5 text-gray-500" />
              )}
            </button>

            {/* Details Content */}
            {showDetails && (
              <div className="mt-4 space-y-3">
                {viewMode === 'daily' ? (
                  // Daily view - show session cards
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                    {todaySessions.map((session: any, idx: number) => (
                      <div
                        key={session.session_id || idx}
                        className="bg-gradient-to-br from-amber-500 to-amber-600 rounded-xl p-4 shadow-md text-white"
                      >
                        <div className="text-xs text-amber-100 mb-1 font-medium">
                          {formatSessionTime(session.timestamp)}
                        </div>
                        <div className="text-xl font-bold mb-1">
                          {formatWeight(session.feed_weight)}
                        </div>
                        <div className="text-sm text-amber-50">
                          {Math.floor(session.eat_duration / 60)} min • {formatSpeed(session.eat_speed)}
                        </div>
                        <div className="text-xs text-amber-100 mt-1">
                          {session.temperature?.toFixed(1) || 'N/A'}°C
                        </div>
                      </div>
                    ))}
                    
                    {todaySessions.length === 0 && (
                      <div className="col-span-full text-center py-8 text-gray-500">
                        No eating sessions recorded today
                      </div>
                    )}
                  </div>
                ) : (
                  // Weekly view - show daily breakdown
                  <div className="space-y-2">
                    {currentWeek.daily_summaries?.map((day: any, idx: number) => {
                      const dayDate = new Date(day.date);
                      const dayName = dayDate.toLocaleDateString('en-US', { weekday: 'short' });
                      const isToday = day.date === new Date().toISOString().split('T')[0];
                      
                      return (
                        <div
                          key={idx}
                          className={`flex items-center justify-between p-4 rounded-lg border ${
                            isToday ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-gray-200'
                          }`}
                        >
                          <div className="flex items-center gap-4">
                            <div className={`text-center ${isToday ? 'text-blue-600' : 'text-gray-700'}`}>
                              <div className="text-xs font-medium uppercase">{dayName}</div>
                              <div className="text-lg font-bold">{dayDate.getDate()}</div>
                            </div>
                            <div>
                              <div className="text-sm font-medium text-gray-900">{day.total_sessions} sessions</div>
                              <div className="text-xs text-gray-500">{formatDuration(day.total_eat_duration)}</div>
                            </div>
                          </div>
                          <div className="flex items-center gap-4">
                            <div className="text-right">
                              <div className="flex items-center gap-1">
                                <Weight className="w-4 h-4 text-amber-500" />
                                <span className="font-semibold text-gray-900">{formatWeight(day.total_feed_weight)}</span>
                              </div>
                              <div className="flex items-center gap-1 mt-1">
                                <Thermometer className="w-3 h-3 text-red-500" />
                                <span className="text-xs text-gray-600">{day.avg_temperature?.toFixed(1) || 'N/A'}°C</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    }) || []}
                  </div>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </section>
  );
}