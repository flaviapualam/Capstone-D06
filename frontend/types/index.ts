// User and Authentication types (Farmer table)
export interface User {
  farmerId: string;
  name: string;
  email: string;
  passwordHash?: string;
  role?: 'admin' | 'user';
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
  cowId: string;
  farmerId: string;
  name: string;
  age: number;
  status: 'healthy' | 'sick' | 'pregnant' | 'injured';
  breed?: string;
  weight?: number;
  lastCheckup?: string;
  notes?: string;
  createdAt?: string;
  updatedAt?: string;
  image?: string;
}

export interface CattleRegistrationData {
  name: string;
  breed: string;
  age: number;
  weight: number;
  status: Cattle['status'];
  notes?: string;
}

// Sensor table
export interface Sensor {
  sensorId: string;
  type: 'feed_intake' | 'activity' | 'temperature' | 'heart_rate';
  status: 'active' | 'inactive' | 'maintenance';
  installDate: string;
  lastCalibration?: string;
}

// Clean Data table
export interface SensorReading {
  timeGenerated: string;
  cowId: string;
  sensorId: string;
  eatDuration: number;
  eatSpeed: number;
  anomalyScore: number;
  temperature?: number;
  heartRate?: number;
  activityLevel?: number;
  location?: {
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