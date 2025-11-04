import { ApiResponse, User, LoginCredentials, RegisterData, Cattle, CattleRegistrationData, SensorReading, Sensor } from '@/types';

// Base API configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

console.log('🔧 API Base URL:', API_BASE_URL);

// Helper function for API calls with credentials
async function apiCall<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const url = `${API_BASE_URL}${endpoint}`;
  console.log('📡 API Call:', options.method || 'GET', url);

  try {
    const response = await fetch(url, {
      ...options,
      credentials: 'include', // Include cookies for authentication
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    console.log('📥 Response status:', response.status, response.statusText);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const errorMessage = errorData.detail || `HTTP ${response.status}: ${response.statusText}`;
      console.error('❌ API Error:', errorMessage, errorData);
      throw new Error(errorMessage);
    }

    const data = await response.json();
    console.log('✅ API Success:', data);
    return {
      success: true,
      data,
    };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'An error occurred';
    console.error('❌ Fetch Error:', errorMessage, error);

    // Check if it's a network error
    if (error instanceof TypeError && error.message.includes('fetch')) {
      return {
        success: false,
        error: 'Cannot connect to backend server. Make sure it\'s running on ' + API_BASE_URL,
      };
    }

    return {
      success: false,
      error: errorMessage,
    };
  }
}

// Authentication API
export const authApi = {
  login: async (credentials: LoginCredentials): Promise<ApiResponse<{ user: User; token: string }>> => {
    const response = await apiCall<any>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });

    if (response.success && response.data) {
      // Backend returns farmer data, transform to User format
      const user: User = {
        farmerId: response.data.farmer_id,
        name: response.data.name,
        email: response.data.email,
        role: 'farmer',
      };
      return {
        success: true,
        data: {
          user,
          token: 'cookie-based', // Backend uses HTTP-only cookies
        },
      };
    }

    return response as ApiResponse<{ user: User; token: string }>;
  },

  register: async (userData: RegisterData): Promise<ApiResponse<{ user: User; token: string }>> => {
    const response = await apiCall<any>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        name: userData.name,
        email: userData.email,
        password: userData.password,
      }),
    });

    if (response.success && response.data) {
      // Backend returns {message, data: {farmer_id, name, email}}
      const farmerData = response.data.data || response.data;
      const user: User = {
        farmerId: farmerData.farmer_id,
        name: farmerData.name,
        email: farmerData.email,
        role: 'farmer',
      };
      return {
        success: true,
        data: {
          user,
          token: 'cookie-based',
        },
      };
    }

    return response as ApiResponse<{ user: User; token: string }>;
  },

  forgotPassword: async (email: string): Promise<ApiResponse<{ message: string }>> => {
    // Not implemented in backend yet
    return {
      success: false,
      error: 'Forgot password feature not yet implemented',
    };
  },

  logout: async (): Promise<ApiResponse<{ message: string }>> => {
    // Clear frontend state (backend doesn't have logout endpoint yet)
    return {
      success: true,
      data: { message: 'Logged out successfully' },
    };
  },
};

// Cattle API (maps to /farm/cow endpoints)
export const cattleApi = {
  getAll: async (farmerId: string): Promise<ApiResponse<Cattle[]>> => {
    const response = await apiCall<any[]>(`/farm/cow?farmer_id=${farmerId}`, {
      method: 'GET',
    });

    if (response.success && response.data) {
      // Transform backend response to frontend Cattle type
      const cattle: Cattle[] = response.data.map((cow: any) => ({
        cowId: cow.cow_id || '',
        farmerId: cow.farmer_id || '',
        name: cow.name || '',
        age: cow.age || 0,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      }));

      return {
        success: true,
        data: cattle,
      };
    }

    return response as ApiResponse<Cattle[]>;
  },

  getByCowId: async (cowId: string): Promise<ApiResponse<Cattle>> => {
    // Backend doesn't have single cow endpoint, use getAll and filter
    return {
      success: false,
      error: 'Get single cow not implemented - use getAll instead',
    };
  },

  getByFarmerId: async (farmerId: string): Promise<ApiResponse<Cattle[]>> => {
    return cattleApi.getAll(farmerId);
  },

  create: async (cattleData: CattleRegistrationData, farmerId: string): Promise<ApiResponse<Cattle>> => {
    const response = await apiCall<any>('/farm/cow', {
      method: 'POST',
      body: JSON.stringify({
        farmer_id: farmerId,
        name: cattleData.name,
        age: cattleData.age,
      }),
    });

    if (response.success && response.data) {
      const cattle: Cattle = {
        cowId: response.data.cow_id || '',
        farmerId: response.data.farmer_id || '',
        name: response.data.name || '',
        age: response.data.age || 0,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      return {
        success: true,
        data: cattle,
      };
    }

    return response as ApiResponse<Cattle>;
  },

  update: async (cowId: string, cattleData: Partial<CattleRegistrationData>): Promise<ApiResponse<Cattle>> => {
    const updatePayload: any = {};
    if (cattleData.name) updatePayload.name = cattleData.name;
    if (cattleData.age) updatePayload.age = cattleData.age;

    const response = await apiCall<any>(`/farm/cow/${cowId}`, {
      method: 'PUT',
      body: JSON.stringify(updatePayload),
    });

    if (response.success && response.data) {
      const cattle: Cattle = {
        cowId: response.data.cow_id || '',
        farmerId: response.data.farmer_id || '',
        name: response.data.name || '',
        age: response.data.age || 0,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      return {
        success: true,
        data: cattle,
      };
    }

    return response as ApiResponse<Cattle>;
  },

  delete: async (cowId: string): Promise<ApiResponse<{ message: string }>> => {
    return apiCall<{ message: string }>(`/farm/cow/${cowId}`, {
      method: 'DELETE',
    });
  },
};

// Sensor API (maps to /farm/sensor endpoints)
export const sensorApi = {
  getAll: async (): Promise<ApiResponse<Sensor[]>> => {
    const response = await apiCall<any[]>('/farm/sensor', {
      method: 'GET',
    });

    if (response.success && response.data) {
      const sensors: Sensor[] = response.data.map((sensor: any) => ({
        sensorId: sensor.sensor_id,
        status: sensor.status === 1 ? 'active' : 'inactive',
      }));

      return {
        success: true,
        data: sensors,
      };
    }

    return response as ApiResponse<Sensor[]>;
  },
};

// Monitoring API (simplified to match backend capabilities)
export const monitoringApi = {
  getSensorData: async (cowId?: number, limit: number = 100): Promise<ApiResponse<SensorReading[]>> => {
    const queryParams = new URLSearchParams();
    if (cowId !== undefined) queryParams.append('cow_id', cowId.toString());
    queryParams.append('limit', limit.toString());

    const response = await apiCall<{ data: any[]; count: number }>(
      `/farm/sensor-data?${queryParams.toString()}`,
      { method: 'GET' }
    );

    if (response.success && response.data) {
      // Transform MongoDB sensor data to frontend SensorReading type
      const sensorReadings: SensorReading[] = response.data.data.map((reading: any) => ({
        timeGenerated: reading.timestamp || reading.timeGenerated || new Date().toISOString(),
        cowId: reading.cow_id?.toString() || reading.cowId || '',
        eatDuration: reading.eat_duration || reading.eatDuration || 0,
        eatSpeed: reading.eat_speed || reading.eatSpeed || 0,
        anomalyScore: reading.anomaly_score || reading.anomalyScore || 0,
        temperature: reading.temperature || 0,
        heartRate: reading.heart_rate || reading.heartRate || 0,
        activityLevel: reading.activity_level || reading.activityLevel || 0,
        location: reading.location || '',
      }));

      return {
        success: true,
        data: sensorReadings,
      };
    }

    return {
      success: false,
      error: response.error || 'Failed to fetch sensor data',
    };
  },

  // Removed unsupported features:
  // - getStatus (no backend endpoint)
  // - getAlerts (no backend endpoint)
  // - getFeedData (no backend endpoint)
  // - getAnomalyScore (can be calculated from sensor data on frontend)
};

// Export a combined API object for backward compatibility
export const api = {
  auth: authApi,
  cattle: cattleApi,
  sensor: sensorApi,
  monitoring: monitoringApi,
};

export default api;
