import { ApiResponse, User, LoginCredentials, RegisterData, Cattle, CattleRegistrationData, SensorReading, Sensor } from '@/types';

// Base API configuration
// Direct backend URL (cross-origin request with credentials)
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://project-capstone.my.id/api';

console.log('API Base URL:', API_BASE_URL);

// Helper function for API calls with credentials
async function apiCall<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const url = `${API_BASE_URL}${endpoint}`;
  console.log('API Call:', options.method || 'GET', url);

  try {
    const response = await fetch(url, {
      ...options,
      credentials: 'include', // Include cookies for authentication
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    console.log('Response status:', response.status, response.statusText);

    // Handle 401 Unauthorized - token expired or invalid
    if (response.status === 401) {
      console.warn('Authentication failed - dispatching logout event');
      // Trigger logout event for AuthProvider to handle
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('auth:unauthorized'));
      }
      return {
        success: false,
        error: 'Session expired. Please login again.',
      };
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMessage = errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`;
      console.error('API Error:', errorMessage, errorData);
      return {
        success: false,
        error: errorMessage,
      };
    }

    // Some endpoints may return empty body
    const contentType = response.headers.get('content-type') || '';
    const data = contentType.includes('application/json') ? await response.json() : undefined;
    console.log('API Success:', data);
    return {
      success: true,
      data: data as T,
    };
  } catch (error: any) {
    console.error('apiCall caught error:', error);
    return {
      success: false,
      error: (error && error.message) || String(error),
    };
  }
}

// Authentication API
export const authApi = {
  login: async (credentials: LoginCredentials): Promise<ApiResponse<{ user: User }>> => {
    // POST to cookie-based login (backend v3 mounted under /api)
    await apiCall<any>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });

    // After cookie set, fetch current farmer data from /api/auth/me
    const meResp = await apiCall<any>('/auth/me', { method: 'GET' });
    if (meResp.success && meResp.data) {
      const farmer = meResp.data;
      const user: User = {
        farmerId: farmer.farmer_id,
        name: farmer.name,
        email: farmer.email,
        role: 'farmer',
      };
      return {
        success: true,
        data: { user },
      };
    }
    return { success: false, error: 'Failed to get user after login' };
  },

  register: async (userData: RegisterData): Promise<ApiResponse<{ user: User }>> => {
    const response = await apiCall<any>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        name: userData.name,
        email: userData.email,
        password: userData.password,
      }),
    });

    if (response.success && response.data) {
      // backend returns FarmerResponse (farmer_id, name, email, created_at)
      const farmer = response.data;
      const user: User = {
        farmerId: farmer.farmer_id,
        name: farmer.name,
        email: farmer.email,
        role: 'farmer',
      };
      return {
        success: true,
        data: { user },
      };
    }
    return { success: false, error: response.error || 'Registration failed' };
  },

  me: async (): Promise<ApiResponse<{ user: User }>> => {
    const meResp = await apiCall<any>('/auth/me', { method: 'GET' });
    if (meResp.success && meResp.data) {
      const farmer = meResp.data;
      const user: User = {
        farmerId: farmer.farmer_id,
        name: farmer.name,
        email: farmer.email,
        role: 'farmer',
      };
      return { success: true, data: { user } };
    }
    return { success: false, error: meResp.error || 'Not authenticated' };
  },

  logout: async (): Promise<ApiResponse<{ message: string }>> => {
    // backend v3 does not expose logout - clear frontend state only
    return { success: true, data: { message: 'Logged out (frontend only)' } };
  },

  forgotPassword: async (email: string): Promise<ApiResponse<{ message: string }>> => {
    // Placeholder - backend does not implement password reset yet
    // When backend adds /api/auth/forgot-password endpoint, uncomment:
    // return apiCall<{ message: string }>('/api/auth/forgot-password', {
    //   method: 'POST',
    //   body: JSON.stringify({ email }),
    // });
    return { 
      success: false, 
      error: 'Password reset not implemented on backend' 
    };
  },
};

// Cattle API (maps to /api/cow endpoints on backend v3)
export const cattleApi = {
  getAll: async (): Promise<ApiResponse<Cattle[]>> => {
    const response = await apiCall<any[]>('/cow/', { method: 'GET' });
    if (response.success && response.data) {
      const cattle: Cattle[] = response.data.map((cow: any) => {
        // Backend returns date_of_birth; compute age if possible
        let age = 0;
        if (cow.date_of_birth) {
          try {
            const dob = new Date(cow.date_of_birth);
            const diff = Date.now() - dob.getTime();
            age = Math.floor(diff / (1000 * 60 * 60 * 24 * 365));
          } catch {
            age = 0;
          }
        }
        return {
          cowId: cow.cow_id || '',
          farmerId: cow.farmer_id || '',
          name: cow.name || '',
          age,
          createdAt: cow.created_at || new Date().toISOString(),
          updatedAt: cow.updated_at || new Date().toISOString(),
        } as Cattle;
      });
      return { success: true, data: cattle };
    }
    return response as ApiResponse<Cattle[]>;
  },

  create: async (cattleData: CattleRegistrationData): Promise<ApiResponse<Cattle>> => {
    const payload: any = { name: cattleData.name };
    
    // Add optional fields if provided
    if (cattleData.date_of_birth) {
      payload.date_of_birth = cattleData.date_of_birth;
    }
    if (cattleData.gender) {
      payload.gender = cattleData.gender;
    }

    const response = await apiCall<any>('/cow/', {
      method: 'POST',
      body: JSON.stringify(payload),
    });

    if (response.success && response.data) {
      const cow = response.data;
      
      // Calculate age from date_of_birth if available
      let age = 0;
      if (cow.date_of_birth) {
        try {
          const dob = new Date(cow.date_of_birth);
          const diff = Date.now() - dob.getTime();
          age = Math.floor(diff / (1000 * 60 * 60 * 24 * 365));
        } catch {
          age = 0;
        }
      }
      
      const cattle: Cattle = {
        cowId: cow.cow_id || '',
        farmerId: cow.farmer_id || '',
        name: cow.name || '',
        date_of_birth: cow.date_of_birth || undefined,
        gender: cow.gender || undefined,
        age,
        createdAt: cow.created_at || new Date().toISOString(),
        updatedAt: cow.updated_at || new Date().toISOString(),
      };
      return { success: true, data: cattle };
    }

    return response as ApiResponse<Cattle>;
  },

  update: async (cowId: string, cattleData: Partial<CattleRegistrationData>): Promise<ApiResponse<Cattle>> => {
    const payload: any = {};
    
    if (cattleData.name) payload.name = cattleData.name;
    if (cattleData.date_of_birth) payload.date_of_birth = cattleData.date_of_birth;
    if (cattleData.gender) payload.gender = cattleData.gender;

    const response = await apiCall<any>(`/cow/${cowId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });

    if (response.success && response.data) {
      const cow = response.data;
      
      // Calculate age from date_of_birth if available
      let age = 0;
      if (cow.date_of_birth) {
        try {
          const dob = new Date(cow.date_of_birth);
          const diff = Date.now() - dob.getTime();
          age = Math.floor(diff / (1000 * 60 * 60 * 24 * 365));
        } catch {
          age = 0;
        }
      }
      
      const cattle: Cattle = {
        cowId: cow.cow_id || '',
        farmerId: cow.farmer_id || '',
        name: cow.name || '',
        date_of_birth: cow.date_of_birth || undefined,
        gender: cow.gender || undefined,
        age,
        createdAt: cow.created_at || new Date().toISOString(),
        updatedAt: cow.updated_at || new Date().toISOString(),
      };
      return { success: true, data: cattle };
    }

    return response as ApiResponse<Cattle>;
  },

  delete: async (cowId: string): Promise<ApiResponse<{ message: string }>> => {
    return apiCall<{ message: string }>(`/cow/${cowId}`, { method: 'DELETE' });
  },
};

// Keep sensor/monitoring stubs unchanged but exported for compatibility
export const sensorApi = {
  getAll: async (): Promise<ApiResponse<Sensor[]>> => {
    const response = await apiCall<any[]>('/sensor', { method: 'GET' });
    if (response.success && response.data) {
      const sensors: Sensor[] = response.data.map((sensor: any) => ({
        sensorId: sensor.sensor_id,
        status: sensor.status === 1 ? 'active' : 'inactive',
      }));
      return { success: true, data: sensors };
    }
    return response as ApiResponse<Sensor[]>;
  },
};

export const monitoringApi = {
  getSensorData: async (cowId?: number, limit: number = 100): Promise<ApiResponse<SensorReading[]>> => {
    const queryParams = new URLSearchParams();
    if (cowId !== undefined) queryParams.append('cow_id', cowId.toString());
    queryParams.append('limit', limit.toString());

    const response = await apiCall<{ data: any[]; count: number }>(`/api/sensor-data?${queryParams.toString()}`, { method: 'GET' });
    if (response.success && response.data) {
      const sensorReadings: SensorReading[] = response.data.data.map((reading: any) => ({
        timeGenerated: reading.timestamp || reading.timeGenerated || new Date().toISOString(),
        cowId: reading.cow_id?.toString() || reading.cowId || reading.rfid_id || '',
        eatDuration: reading.eat_duration || reading.eatDuration || 0,
        eatSpeed: reading.eat_speed || reading.eatSpeed || 0,
        feedWeight: reading.feed_weight || reading.feedWeight || 0,
        anomalyScore: reading.anomaly_score || reading.anomalyScore || 0,
        temperature: reading.temperature_c || reading.temperature || 0,
        location: reading.location || reading.ip || '',
      }));
      return { success: true, data: sensorReadings };
    }
    return { success: false, error: response.error || 'Failed to fetch sensor data' };
  },

  // Historical data - fetch with different time ranges
  getSensorHistory: async (cowId: string, timeRange: string = 'all'): Promise<ApiResponse<SensorReading[]>> => {
    // Convert timeRange to hours parameter (backend max is 720 hours = 30 days)
    const hoursMap: Record<string, number> = {
      'today': 24,
      '2days': 48,
      '7days': 168,   // 7 * 24
      '30days': 720,  // 30 * 24
      'all': 720      // Max 30 days
    };
    
    const hours = hoursMap[timeRange] || 24;
    const url = `/cow/${cowId}/sensor_history?hours=${hours}`;
    
    console.log('Calling sensor history API:', url);
    
    const response = await apiCall<any[]>(url, { 
      method: 'GET' 
    });
    
    console.log('Sensor history API response:', response);
    
    if (response.success && response.data) {
      const sensorReadings: SensorReading[] = response.data.map((reading: any) => ({
        timeGenerated: reading.timestamp || reading.time_generated || new Date().toISOString(),
        cowId: reading.cow_id?.toString() || cowId,
        eatDuration: reading.eat_duration || 0,
        eatSpeed: reading.eat_speed || 0,
        feedWeight: reading.feed_weight || reading.weight || 0,
        anomalyScore: reading.anomaly_score || 0,
        temperature: reading.temperature || reading.temperature_c || 0,
        location: reading.location || '',
        isAnomaly: reading.is_anomaly || false,
      }));
      return { success: true, data: sensorReadings };
    }
    return { success: false, error: response.error || 'Failed to fetch sensor history' };
  },

  // Live streaming with SSE - returns EventSource for real-time updates
  createLiveStream: (
    cowId: string, 
    onData: (reading: SensorReading) => void, 
    onError?: (error: string) => void,
    onOpen?: () => void
  ): EventSource => {
    const url = `${API_BASE_URL}/streaming/cows/${cowId}`;
    console.log('Creating SSE connection:', url);
    
    const eventSource = new EventSource(url, { withCredentials: true });
    
    eventSource.onopen = () => {
      console.log('✅ SSE connection established');
      onOpen?.();
    };
    
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('SSE data received:', data);
        
        // Map backend data to SensorReading
        const reading: SensorReading = {
          timeGenerated: data.timestamp || data.time_generated || new Date().toISOString(),
          cowId: data.cow_id?.toString() || cowId,
          eatDuration: data.eat_duration || 0,
          eatSpeed: data.eat_speed || 0,
          feedWeight: data.feed_weight || data.weight || 0,
          anomalyScore: data.anomaly_score || 0,
          temperature: data.temperature || data.temperature_c || 0,
          location: data.location || data.ip || '',
          isAnomaly: data.is_anomaly || false,
        };
        
        onData(reading);
      } catch (error) {
        console.error('Error parsing SSE data:', error);
        onError?.('Failed to parse sensor data');
      }
    };
    
    eventSource.onerror = (error) => {
      console.error('❌ SSE connection error:', error);
      const errorMsg = eventSource.readyState === EventSource.CLOSED 
        ? 'Connection closed by server' 
        : 'Failed to connect to sensor stream';
      onError?.(errorMsg);
    };
    
    return eventSource; // Return EventSource for cleanup
  },
};

// RFID API (maps to /api/rfid endpoints on backend v3)
export const rfidApi = {
  assign: async (rfidId: string, cowId: string): Promise<ApiResponse<any>> => {
    return apiCall<any>('/rfid/assign', {
      method: 'POST',
      body: JSON.stringify({
        rfid_id: rfidId,
        cow_id: cowId,
      }),
    });
  },
};

// Pregnancy API (maps to /api/cow/{cow_id}/pregnancies endpoints)
export const pregnancyApi = {
  getAll: async (cowId: string): Promise<ApiResponse<any[]>> => {
    // Get pregnancies from the cow data itself (GET /api/cow/ returns pregnancies array)
    const response = await apiCall<any[]>('/cow/', {
      method: 'GET',
    });
    
    if (response.success && response.data) {
      // Find the specific cow and return its pregnancies
      const cow = response.data.find((c: any) => c.cow_id === cowId);
      if (cow && cow.pregnancies) {
        return { success: true, data: cow.pregnancies };
      }
      return { success: true, data: [] }; // No pregnancies found
    }
    
    return { success: false, error: response.error || 'Failed to fetch pregnancies' };
  },

  create: async (cowId: string, pregnancyData: {
    time_start: string;
    expected_due_date?: string;
  }): Promise<ApiResponse<any>> => {
    return apiCall<any>(`/cow/${cowId}/pregnancies`, {
      method: 'POST',
      body: JSON.stringify(pregnancyData),
    });
  },

  update: async (cowId: string, pregnancyId: number, pregnancyData: {
    time_end?: string;
    status?: string;
  }): Promise<ApiResponse<any>> => {
    return apiCall<any>(`/cow/${cowId}/pregnancies/${pregnancyId}`, {
      method: 'PATCH',
      body: JSON.stringify(pregnancyData),
    });
  },

  delete: async (cowId: string, pregnancyId: number): Promise<ApiResponse<any>> => {
    return apiCall<any>(`/cow/${cowId}/pregnancies/${pregnancyId}`, {
      method: 'DELETE',
    });
  },
};

// ML/Anomaly API (maps to /api/ml/anomaly endpoints)
export const mlApi = {
  // Get all anomalies (optionally filter by cow_id)
  getAnomalies: async (cowId?: string): Promise<ApiResponse<any[]>> => {
    let url = '/ml/anomaly';
    if (cowId) {
      url += `?cow_id=${cowId}`;
    }
    
    const response = await apiCall<{ anomalies: any[] }>(url, { 
      method: 'GET' 
    });
    
    if (response.success && response.data) {
      // Map anomalies and add severity based on score
      const anomalies = response.data.anomalies.map((anomaly: any) => ({
        ...anomaly,
        severity: anomaly.anomaly_score > -0.2 ? 'high' : 
                  anomaly.anomaly_score > -0.4 ? 'medium' : 'low',
      }));
      
      return { success: true, data: anomalies };
    }
    return { success: false, error: response.error || 'Failed to fetch anomalies' };
  },

  // Resend email alert for specific anomaly
  resendAnomalyEmail: async (anomalyId: number): Promise<ApiResponse<any>> => {
    const response = await apiCall<any>(`/anomaly/${anomalyId}/send-alert`, {
      method: 'POST',
    });
    
    return response;
  },
};

// Eating Session API (for MonitoringSection)
export const eatingSessionApi = {
  // Get all sessions for a cow (optional date range)
  getSessions: async (
    cowId: string, 
    startDate?: string, 
    endDate?: string
  ): Promise<ApiResponse<any[]>> => {
    let url = `/cow/${cowId}/eating-sessions`;
    const params = new URLSearchParams();
    
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    
    if (params.toString()) url += `?${params.toString()}`;
    
    const response = await apiCall<{ sessions: any[] }>(url, { method: 'GET' });
    if (response.success && response.data) {
      return { success: true, data: response.data.sessions };
    }
    return { success: false, error: response.error || 'Failed to fetch eating sessions' };
  },

  // Get daily summary (last N days)
  getDailySummary: async (cowId: string, days: number = 7): Promise<ApiResponse<any>> => {
    const url = `/cow/${cowId}/daily-summary?days=${days}`;
    const response = await apiCall<any>(url, { method: 'GET' });
    
    if (response.success && response.data) {
      return { success: true, data: response.data };
    }
    return { success: false, error: response.error || 'Failed to fetch daily summary' };
  },

  // Get weekly summary (current week + previous week)
  getWeeklySummary: async (cowId: string, weeks: number = 2): Promise<ApiResponse<any>> => {
    const url = `/cow/${cowId}/weekly-summary?weeks=${weeks}`;
    const response = await apiCall<any>(url, { method: 'GET' });
    
    if (response.success && response.data) {
      return { success: true, data: response.data };
    }
    return { success: false, error: response.error || 'Failed to fetch weekly summary' };
  },
};

export const api = {
  auth: authApi,
  cattle: cattleApi,
  sensor: sensorApi,
  monitoring: monitoringApi,
  rfid: rfidApi,
  pregnancy: pregnancyApi,
  ml: mlApi,
  eatingSession: eatingSessionApi,
};

export default api;

