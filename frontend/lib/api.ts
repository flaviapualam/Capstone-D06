import { ApiResponse, User, LoginCredentials, RegisterData, Cattle, CattleRegistrationData, SensorReading, Sensor } from '@/types';

// Base API configuration
// Use relative base by default so browser requests go to the same origin
// (Next.js can rewrite `/api/*` to an external backend during development).
// If NEXT_PUBLIC_API_URL is set (e.g., production), use that instead.
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? '';

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
    await apiCall<any>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });

    // After cookie set, fetch current farmer data from /api/auth/me
    const meResp = await apiCall<any>('/api/auth/me', { method: 'GET' });
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
    const response = await apiCall<any>('/api/auth/register', {
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
    const meResp = await apiCall<any>('/api/auth/me', { method: 'GET' });
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
};

// Cattle API (maps to /api/cow endpoints on backend v3)
export const cattleApi = {
  getAll: async (): Promise<ApiResponse<Cattle[]>> => {
    const response = await apiCall<any[]>('/api/cow', { method: 'GET' });
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

    const response = await apiCall<any>('/api/cow', {
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

    const response = await apiCall<any>(`/api/cow/${cowId}`, {
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
    return apiCall<{ message: string }>(`/api/cow/${cowId}`, { method: 'DELETE' });
  },
};

// Keep sensor/monitoring stubs unchanged but exported for compatibility
export const sensorApi = {
  getAll: async (): Promise<ApiResponse<Sensor[]>> => {
    const response = await apiCall<any[]>('/api/sensor', { method: 'GET' });
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
        anomalyScore: reading.anomaly_score || reading.anomalyScore || 0,
        temperature: reading.temperature_c || reading.temperature || 0,
        location: reading.location || reading.ip || '',
      }));
      return { success: true, data: sensorReadings };
    }
    return { success: false, error: response.error || 'Failed to fetch sensor data' };
  },
};

export const api = {
  auth: authApi,
  cattle: cattleApi,
  sensor: sensorApi,
  monitoring: monitoringApi,
};

export default api;

