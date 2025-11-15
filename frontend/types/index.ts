// User and Authentication types (Farmer table)
export interface User {
  farmerId: string;
  name: string;
  email: string;
  passwordHash?: string;
  role?: 'admin' | 'user' | 'farmer';
  createdAt?: string;
  updatedAt?: string;
}

// Authentication types
export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
}

export interface AuthResponse {
  user: User;
  token?: string;
  message?: string;
}

// Cattle related types (Cow table)
export interface Cattle {
  cowId: string; // UUID from backend (internal identifier)
  farmerId: string; // UUID
  name: string;
  date_of_birth?: string; // YYYY-MM-DD format from backend
  gender?: 'MALE' | 'FEMALE'; // Backend uses Literal['MALE', 'FEMALE']
  age?: number; // Computed field (for display)
  createdAt?: string;
  updatedAt?: string;
}

export interface CattleRegistrationData {
  name: string;
  date_of_birth?: string;
  gender?: 'MALE' | 'FEMALE';
}

// Sensor table (matches backend SensorResponse)
export interface Sensor {
  sensorId: string; // UUID from backend
  status: 'active' | 'inactive'; // Backend uses 1=active, 0=inactive
}

// Clean Data table
export interface SensorReading {
  timeGenerated: string;
  cowId: string;
  sensorId?: string; // Optional - not always provided by backend
  eatDuration: number;
  eatSpeed: number;
  anomalyScore: number;
  temperature?: number;
  location?: string | {
    latitude: number;
    longitude: number;
  };
  isAnomaly?: boolean;
}

// Model AI table
export interface ModelAI {
  modelId: string;
  cowId: string;
  model: string;
  accuracy?: number;
  lastTrained?: string;
  status: 'active' | 'training' | 'inactive';
}

// Monitoring types
export interface Alert {
  id: string;
  cowId: string;
  type: 'health' | 'feeding' | 'location' | 'temperature' | 'system' | 'monitoring';
  severity: 'low' | 'medium' | 'high';
  message: string;
  isResolved: boolean;
  createdAt: string;
  resolvedAt?: string;
}

export interface CattleStatus {
  cowId: string;
  cattle: Cattle;
  currentHealth: 'excellent' | 'good' | 'fair' | 'poor';
  lastReading: SensorReading;
  alerts: Alert[];
  avgEatDuration?: number;
  avgEatSpeed?: number;
  anomalyScore?: number;
  feedingPattern?: string;
  weightTrend?: 'increasing' | 'stable' | 'decreasing';
}

// API Response types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}