'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { AlertTriangle, CheckCircle, X, ChevronDown, ChevronUp } from 'lucide-react';
import { Alert } from '@/types';
import { monitoringApi } from '@/lib/api';

export default function AlertsSection() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAllActive, setShowAllActive] = useState(false);
  const [showAllResolved, setShowAllResolved] = useState(false);

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const response = await monitoringApi.getAlerts();
        if (response.success && response.data) {
          setAlerts(response.data);
        }
      } catch (error) {
        console.error('Error fetching alerts:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAlerts();
    const interval = setInterval(fetchAlerts, 30000); // Refresh every 30 seconds

    return () => clearInterval(interval);
  }, []);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getTimeAgo = (timestamp: string) => {
    const now = new Date();
    const alertTime = new Date(timestamp);
    const diffInMinutes = Math.floor((now.getTime() - alertTime.getTime()) / (1000 * 60));
    
    if (diffInMinutes < 1) return 'Just now';
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
    const diffInHours = Math.floor(diffInMinutes / 60);
    if (diffInHours < 24) return `${diffInHours}h ago`;
    const diffInDays = Math.floor(diffInHours / 24);
    return `${diffInDays}d ago`;
  };

  const activeAlerts = alerts.filter(alert => !alert.isResolved);
  const resolvedAlerts = alerts.filter(alert => alert.isResolved);

  if (loading) {
    return (
      <section className="space-y-6">
        <h2 className="text-2xl font-bold text-gray-900">Alerts & Notifications</h2>
        <Card>
          <CardContent className="p-6">
            <div className="space-y-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-16 bg-gray-100 animate-pulse rounded"></div>
              ))}
            </div>
          </CardContent>
        </Card>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Alerts & Notifications</h2>
        {activeAlerts.length > 0 && (
          <Badge variant="destructive" className="flex items-center space-x-1">
            <AlertTriangle className="w-3 h-3" />
            <span>{activeAlerts.length} Active</span>
          </Badge>
        )}
      </div>

      {activeAlerts.length === 0 && resolvedAlerts.length === 0 ? (
        <Card>
          <CardContent className="p-6 text-center">
            <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
            <h3 className="text-lg font-medium text-gray-900 mb-1">All Clear!</h3>
            <p className="text-gray-600">No active alerts at this time.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {/* Active Alerts */}
          {activeAlerts.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg text-red-700 flex items-center space-x-2">
                  <AlertTriangle className="w-5 h-5" />
                  <span>Active Alerts</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {(showAllActive ? activeAlerts : activeAlerts.slice(0, 3)).map((alert) => (
                  <div
                    key={alert.id}
                    className="flex items-center justify-between p-4 border rounded-lg bg-white hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex-1">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <p className="font-medium text-gray-900">{alert.message}</p>
                          <div className="flex items-center space-x-3 mt-1">
                            <span className="text-sm text-gray-600">
                              Cattle ID: {alert.cowId}
                            </span>
                            <Badge className={getSeverityColor(alert.severity)}>
                              {alert.severity}
                            </Badge>
                            <span className="text-sm text-gray-500">
                              {getTimeAgo(alert.createdAt)}
                            </span>
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="ml-2 text-gray-400 hover:text-gray-600"
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
                {activeAlerts.length > 3 && (
                  <Button
                    variant="ghost"
                    className="w-full mt-3 text-sm text-gray-600 hover:text-gray-900"
                    onClick={() => setShowAllActive(!showAllActive)}
                  >
                    {showAllActive ? (
                      <>
                        <ChevronUp className="w-4 h-4 mr-1" />
                        Show Less
                      </>
                    ) : (
                      <>
                        <ChevronDown className="w-4 h-4 mr-1" />
                        Show {activeAlerts.length - 3} More Alerts
                      </>
                    )}
                  </Button>
                )}
              </CardContent>
            </Card>
          )}

          {/* Resolved Alerts */}
          {resolvedAlerts.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg text-gray-600 flex items-center space-x-2">
                  <CheckCircle className="w-5 h-5" />
                  <span>Recently Resolved</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {(showAllResolved ? resolvedAlerts : resolvedAlerts.slice(0, 3)).map((alert) => (
                  <div
                    key={alert.id}
                    className="flex items-center p-4 border rounded-lg bg-gray-50 opacity-75"
                  >
                    <div className="flex-1">
                      <p className="text-gray-700">{alert.message}</p>
                      <div className="flex items-center space-x-3 mt-1">
                        <span className="text-sm text-gray-500">
                          Cattle ID: {alert.cowId}
                        </span>
                        <Badge variant="outline" className="text-gray-500">
                          {alert.severity}
                        </Badge>
                        <span className="text-sm text-gray-500">
                          {getTimeAgo(alert.createdAt)}
                        </span>
                      </div>
                    </div>
                    <CheckCircle className="w-5 h-5 text-green-500 ml-2" />
                  </div>
                ))}
                {resolvedAlerts.length > 3 && (
                  <Button
                    variant="ghost"
                    className="w-full mt-3 text-sm text-gray-600 hover:text-gray-900"
                    onClick={() => setShowAllResolved(!showAllResolved)}
                  >
                    {showAllResolved ? (
                      <>
                        <ChevronUp className="w-4 h-4 mr-1" />
                        Show Less
                      </>
                    ) : (
                      <>
                        <ChevronDown className="w-4 h-4 mr-1" />
                        Show {resolvedAlerts.length - 3} More Resolved
                      </>
                    )}
                  </Button>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </section>
  );
}
