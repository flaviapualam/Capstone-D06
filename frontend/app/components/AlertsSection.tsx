'use client';

import { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Bell, AlertTriangle, Mail, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';

interface Anomaly {
  anomaly_id: number;
  session_id: number;
  cow_id: string;
  cow_name?: string;
  anomaly_score: number;
  detected_at: string;
  farmer_email?: string;
  avg_temperature?: number;
  severity: 'high' | 'medium' | 'low';
  isRead?: boolean;
}

interface AlertsSectionProps {
  selectedCowId?: string;
  onShowToast?: (message: string, type: 'success' | 'error') => void;
}

export default function AlertsSection({ selectedCowId, onShowToast }: AlertsSectionProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [alerts, setAlerts] = useState<Anomaly[]>([]);
  const [loading, setLoading] = useState(true);
  const [resendingEmail, setResendingEmail] = useState<number | null>(null);

  // Fetch anomalies from API
  useEffect(() => {
    const fetchAlerts = async () => {
      setLoading(true);
      try {
        const response = await api.ml.getAnomalies(selectedCowId);
        if (response.success && response.data) {
          // Add isRead property (default to false for new alerts)
          const alertsWithReadState = response.data.map((alert: any) => ({
            ...alert,
            isRead: false, // In production, you'd track this in backend/localStorage
          }));
          setAlerts(alertsWithReadState);
        } else {
          console.error('Failed to fetch alerts:', response.error);
        }
      } catch (error) {
        console.error('Error fetching alerts:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchAlerts();
    
    // Refresh alerts every 30 seconds
    const interval = setInterval(fetchAlerts, 30000);
    return () => clearInterval(interval);
  }, [selectedCowId]);

  const unreadCount = alerts.filter(a => !a.isRead).length;

  const handleMarkAsRead = (anomalyId: number) => {
    setAlerts(alerts.map(alert => 
      alert.anomaly_id === anomalyId ? { ...alert, isRead: true } : alert
    ));
  };

  const handleMarkAllAsRead = () => {
    setAlerts(alerts.map(alert => ({ ...alert, isRead: true })));
  };

  const handleResendEmail = async (alert: Anomaly) => {
    if (!alert.farmer_email) {
      onShowToast?.('No farmer email configured for this alert', 'error');
      return;
    }

    setResendingEmail(alert.anomaly_id);

    try {
      const response = await api.ml.resendAnomalyEmail(alert.anomaly_id);
      
      if (response.success) {
        onShowToast?.(`✓ Alert email sent to ${alert.farmer_email}`, 'success');
      } else {
        onShowToast?.(response.error || 'Failed to send email', 'error');
      }
    } catch (error) {
      console.error('Error sending email:', error);
      onShowToast?.('Network error while sending email', 'error');
    } finally {
      setResendingEmail(null);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return 'border-red-500 bg-red-50';
      case 'medium': return 'border-yellow-500 bg-yellow-50';
      case 'low': return 'border-blue-500 bg-blue-50';
      default: return 'border-gray-300 bg-gray-50';
    }
  };

  const getSeverityBadge = (severity: string) => {
    const colors = {
      high: 'bg-red-200 text-red-800',
      medium: 'bg-yellow-200 text-yellow-800',
      low: 'bg-blue-200 text-blue-800',
    };
    return colors[severity as keyof typeof colors] || 'bg-gray-200 text-gray-800';
  };

  const formatAlertTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="sm"
        className="relative p-2 hover:bg-gray-100"
        onClick={() => setIsOpen(!isOpen)}
        title="View alerts"
      >
        <Bell className="w-5 h-5 text-yellow-800" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold">
            {unreadCount}
          </span>
        )}
      </Button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />

          <Card className="absolute right-0 top-12 w-96 max-h-[600px] shadow-lg border z-20 bg-white overflow-hidden flex flex-col">
            <CardHeader className="border-b flex-shrink-0">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center space-x-2">
                  <Bell className="w-5 h-5" />
                  <span>Alerts</span>
                  {unreadCount > 0 && (
                    <span className="bg-red-500 text-white text-xs rounded-full px-2 py-0.5">
                      {unreadCount} new
                    </span>
                  )}
                </CardTitle>
                {unreadCount > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleMarkAllAsRead}
                    className="text-xs text-blue-600 hover:text-blue-800"
                  >
                    Mark all as read
                  </Button>
                )}
              </div>
            </CardHeader>

            <CardContent className="p-0 overflow-y-auto flex-1">
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
                </div>
              ) : alerts.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <Bell className="w-12 h-12 mx-auto mb-2 text-gray-300" />
                  <p className="text-sm font-medium">No anomalies detected</p>
                  <p className="text-xs text-gray-400 mt-1">All cattle feeding patterns are normal</p>
                </div>
              ) : (
                <div className="divide-y">
                  {alerts.map((alert) => (
                    <div
                      key={alert.anomaly_id}
                      className={`p-4 transition-colors ${
                        !alert.isRead ? 'bg-blue-50/50' : 'hover:bg-gray-50'
                      }`}
                    >
                      {/* Alert Header */}
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <AlertTriangle className={`w-4 h-4 ${
                              alert.severity === 'high' ? 'text-red-600' :
                              alert.severity === 'medium' ? 'text-yellow-600' : 'text-blue-600'
                            }`} />
                            <span className="font-semibold text-sm text-gray-900">
                              {alert.cow_name || `Cow ${alert.cow_id}`}
                            </span>
                          </div>
                          <p className="text-xs text-gray-500">
                            Session ID: {alert.session_id} • {formatAlertTime(alert.detected_at)}
                          </p>
                        </div>
                        
                        <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getSeverityBadge(alert.severity)}`}>
                          {alert.severity.toUpperCase()}
                        </span>
                      </div>

                      {/* Alert Metrics */}
                      <div className="grid grid-cols-2 gap-2 mb-3">
                        <div className="bg-white p-2 rounded border border-gray-200">
                          <p className="text-xs text-gray-600">🌡️ Avg Temp</p>
                          <p className="font-semibold text-sm">
                            {alert.avg_temperature?.toFixed(2) || 'N/A'}°C
                          </p>
                        </div>
                        <div className="bg-white p-2 rounded border border-gray-200">
                          <p className="text-xs text-gray-600">📊 Score</p>
                          <p className="font-semibold text-sm">
                            {alert.anomaly_score?.toFixed(4) || 'N/A'}
                          </p>
                        </div>
                      </div>

                      {/* Email Alert Section */}
                      <div className="pt-3 border-t border-gray-200">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2 text-xs">
                            <Mail className="w-3 h-3 text-gray-500" />
                            {alert.farmer_email ? (
                              <span className="text-gray-700 font-medium">
                                {alert.farmer_email}
                              </span>
                            ) : (
                              <span className="text-gray-400 italic">No email</span>
                            )}
                          </div>

                          <div className="flex items-center gap-2">
                            {!alert.isRead && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleMarkAsRead(alert.anomaly_id)}
                                className="text-xs h-7 px-2 text-blue-600 hover:text-blue-800"
                              >
                                Mark read
                              </Button>
                            )}
                            
                            {alert.farmer_email && (
                              <Button
                                size="sm"
                                onClick={() => handleResendEmail(alert)}
                                disabled={resendingEmail === alert.anomaly_id}
                                className={`text-xs h-7 px-3 ${
                                  resendingEmail === alert.anomaly_id
                                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                                    : 'bg-blue-500 hover:bg-blue-600 text-white'
                                }`}
                              >
                                {resendingEmail === alert.anomaly_id ? (
                                  <span className="flex items-center gap-1">
                                    <Loader2 className="w-3 h-3 animate-spin" />
                                    Sending...
                                  </span>
                                ) : (
                                  <span className="flex items-center gap-1">
                                    <Mail className="w-3 h-3" />
                                    Resend
                                  </span>
                                )}
                              </Button>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}