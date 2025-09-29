import { ApiResponse, User, LoginCredentials, RegisterData, Cattle, CattleRegistrationData, SensorReading, Alert, CattleStatus } from '@/types';
import { mockLogin, mockRegister, mockCattle, mockSensorReadings, mockAlerts, mockCattleStatus, cattleFeedData } from './mock-data';

// Base API configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

// Mock API delay
const mockApiCall = async <T>(fn: () => T): Promise<ApiResponse<T>> => {
  await new Promise(resolve => setTimeout(resolve, 500));
  try {
    const result = fn();
    return {
      success: true,
      data: result,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'An error occurred',
    };
  }
};

// Authentication API
export const authApi = {
  login: async (credentials: LoginCredentials): Promise<ApiResponse<{ user: User; token: string }>> => {
    try {
      const result = await mockLogin(credentials.email, credentials.password);
      return {
        success: true,
        data: result,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Login failed',
      };
    }
  },

  register: async (userData: RegisterData): Promise<ApiResponse<{ user: User; token: string }>> => {
    try {
      const result = await mockRegister(userData);
      return {
        success: true,
        data: result,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Registration failed',
      };
    }
  },

  forgotPassword: async (email: string): Promise<ApiResponse<{ message: string }>> => {
    return mockApiCall(() => ({
      message: 'Password reset email sent successfully',
    }));
  },

  logout: async (): Promise<ApiResponse<{ message: string }>> => {
    return mockApiCall(() => ({
      message: 'Logged out successfully',
    }));
  },
};

// Cattle API (using cowId from ERD)
export const cattleApi = {
  getAll: async (): Promise<ApiResponse<Cattle[]>> => {
    return mockApiCall(() => mockCattle);
  },

  getByCowId: async (cowId: string): Promise<ApiResponse<Cattle>> => {
    return mockApiCall(() => {
      const cattle = mockCattle.find(c => c.cowId === cowId);
      if (!cattle) throw new Error('Cattle not found');
      return cattle;
    });
  },

  getByFarmerId: async (farmerId: string): Promise<ApiResponse<Cattle[]>> => {
    return mockApiCall(() => {
      return mockCattle.filter(c => c.farmerId === farmerId);
    });
  },

  create: async (cattleData: CattleRegistrationData): Promise<ApiResponse<Cattle>> => {
    return mockApiCall(() => {
      const newCattle: Cattle = {
        cowId: `COW-${String(mockCattle.length + 1).padStart(3, '0')}`,
        farmerId: 'FARMER-001', // Default to first farmer
        name: cattleData.name,
        breed: cattleData.breed,
        age: cattleData.age,
        weight: cattleData.weight,
        status: cattleData.status,
        notes: cattleData.notes,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      mockCattle.push(newCattle);
      return newCattle;
    });
  },

  update: async (cowId: string, cattleData: Partial<CattleRegistrationData>): Promise<ApiResponse<Cattle>> => {
    return mockApiCall(() => {
      const index = mockCattle.findIndex(c => c.cowId === cowId);
      if (index === -1) throw new Error('Cattle not found');
      
      mockCattle[index] = {
        ...mockCattle[index],
        ...cattleData,
        updatedAt: new Date().toISOString(),
      };
      return mockCattle[index];
    });
  },

  delete: async (cowId: string): Promise<ApiResponse<{ message: string }>> => {
    return mockApiCall(() => {
      const index = mockCattle.findIndex(c => c.cowId === cowId);
      if (index === -1) throw new Error('Cattle not found');
      
      mockCattle.splice(index, 1);
      return { message: 'Cattle deleted successfully' };
    });
  },
};

// Monitoring API (updated for ERD structure)
export const monitoringApi = {
  getStatus: async (): Promise<ApiResponse<CattleStatus[]>> => {
    return mockApiCall(() => mockCattleStatus);
  },

  getSensorData: async (cowId?: string): Promise<ApiResponse<SensorReading[]>> => {
    return mockApiCall(() => {
      if (cowId) {
        return mockSensorReadings.filter(reading => reading.cowId === cowId);
      }
      return mockSensorReadings;
    });
  },

  getSensorDataByTimeRange: async (
    cowId: string, 
    startTime: string, 
    endTime: string
  ): Promise<ApiResponse<SensorReading[]>> => {
    return mockApiCall(() => {
      return mockSensorReadings.filter(reading => 
        reading.cowId === cowId &&
        reading.timeGenerated >= startTime &&
        reading.timeGenerated <= endTime
      );
    });
  },

  getAlerts: async (): Promise<ApiResponse<Alert[]>> => {
    return mockApiCall(() => mockAlerts);
  },

  getAlertsByCowId: async (cowId: string): Promise<ApiResponse<Alert[]>> => {
    return mockApiCall(() => {
      return mockAlerts.filter(alert => alert.cowId === cowId);
    });
  },

  resolveAlert: async (alertId: string): Promise<ApiResponse<Alert>> => {
    return mockApiCall(() => {
      const alert = mockAlerts.find(a => a.id === alertId);
      if (!alert) throw new Error('Alert not found');
      
      alert.isResolved = true;
      alert.resolvedAt = new Date().toISOString();
      return alert;
    });
  },

  getFeedData: async (cowId?: string): Promise<ApiResponse<any>> => {
    return mockApiCall(() => {
      if (cowId && cattleFeedData[cowId as keyof typeof cattleFeedData]) {
        return cattleFeedData[cowId as keyof typeof cattleFeedData];
      }
      return cattleFeedData;
    });
  },

  getAnomalyScore: async (cowId: string): Promise<ApiResponse<{ score: number; status: string }>> => {
    return mockApiCall(() => {
      const cattleReadings = mockSensorReadings.filter(r => r.cowId === cowId);
      const avgScore = cattleReadings.reduce((sum, r) => sum + r.anomalyScore, 0) / cattleReadings.length || 0;
      
      let status = 'normal';
      if (avgScore > 0.7) status = 'high';
      else if (avgScore > 0.3) status = 'medium';
      
      return { 
        score: Math.round(avgScore * 100) / 100,
        status 
      };
    });
  },
};

// Export a combined API object for backward compatibility
export const api = {
  auth: authApi,
  cattle: cattleApi,
  monitoring: monitoringApi,
};

export default api;