import { User, Cattle, SensorReading, Alert, CattleStatus, Sensor, ModelAI } from '@/types';
import { generateId } from './utils';

// Mock users (Farmer table)
export const mockUsers: User[] = [
  {
    farmerId: 'FARMER-001',
    email: 'admin@cattle-monitor.com',
    name: 'Admin User',
    role: 'admin',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T00:00:00Z',
  },
  {
    farmerId: 'FARMER-002',
    email: 'user@cattle-monitor.com',
    name: 'Regular User',
    role: 'user',
    createdAt: '2024-01-02T00:00:00Z',
    updatedAt: '2024-01-02T00:00:00Z',
  },
];

// Mock cattle data (Cow table) - updated to match ERD
export const mockCattle: Cattle[] = [
  {
    cowId: 'COW-001',
    farmerId: 'FARMER-001',
    name: 'Bella',
    age: 4,
    status: 'healthy',
    breed: 'Holstein',
    weight: 650,
    lastCheckup: '2024-12-19T10:00:00Z',
    notes: 'Pola makan normal, semua sensor berfungsi',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-12-19T10:00:00Z',
    image: 'https://images.unsplash.com/photo-1719357855788-c358f653d549?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxjYXR0bGUlMjBjb3clMjBmYXJtfGVufDF8fHx8MTc1ODAxODEzOXww&ixlib=rb-4.1.0&q=80&w=1080',
  },
  {
    cowId: 'COW-002',
    farmerId: 'FARMER-001',
    name: 'Daisy',
    age: 3,
    status: 'sick',
    breed: 'Angus',
    weight: 580,
    lastCheckup: '2024-12-19T16:30:00Z',
    notes: 'Konsumsi pakan rendah terdeteksi, sensor aktivitas menunjukkan penurunan gerakan',
    createdAt: '2024-02-01T00:00:00Z',
    updatedAt: '2024-12-19T16:30:00Z',
    image: 'https://images.unsplash.com/photo-1570521666179-a8c1bcb6fd90?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxkYWlyeSUyMGNvdyUyMGJsYWNrJTIwd2hpdGV8ZW58MXx8fHwxNzU4MDE4MTQwfDA&ixlib=rb-4.1.0&q=80&w=1080',
  },
  {
    cowId: 'COW-003',
    farmerId: 'FARMER-001',
    name: 'Molly',
    age: 5,
    status: 'healthy',
    breed: 'Jersey',
    weight: 750,
    lastCheckup: '2024-12-19T14:20:00Z',
    notes: 'Waktu makan teratur, tidak ada anomali. Konsumsi berlebih terdeteksi pada malam hari',
    createdAt: '2024-03-01T00:00:00Z',
    updatedAt: '2024-12-19T14:20:00Z',
    image: 'https://images.unsplash.com/photo-1660011569989-965df11d00af?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxicm93biUyMGNvdyUyMGxpdmVzdG9ja3xlbnwxfHx8fDE3NTgwMTgxNDB8MA&ixlib=rb-4.1.0&q=80&w=1080',
  },
];

// Mock sensors (Sensor table)
export const mockSensors: Sensor[] = [
  {
    sensorId: 'SENSOR-001',
    type: 'feed_intake',
    status: 'active',
    installDate: '2024-01-01T00:00:00Z',
    lastCalibration: '2024-12-01T00:00:00Z',
  },
  {
    sensorId: 'SENSOR-002',
    type: 'activity',
    status: 'active',
    installDate: '2024-01-01T00:00:00Z',
    lastCalibration: '2024-12-01T00:00:00Z',
  },
  {
    sensorId: 'SENSOR-003',
    type: 'temperature',
    status: 'active',
    installDate: '2024-01-01T00:00:00Z',
    lastCalibration: '2024-12-01T00:00:00Z',
  },
];

// Enhanced sensor readings (Clean Data table) - matching ERD structure
export const mockSensorReadings: SensorReading[] = [
  // COW-001 data with eating patterns
  {
    timeGenerated: '2024-12-19T06:00:00Z',
    cowId: 'COW-001',
    sensorId: 'SENSOR-001',
    eatDuration: 42, // minutes
    eatSpeed: 4.2, // kg/hour
    anomalyScore: 0.1,
    temperature: 38.5,
    heartRate: 72,
    activityLevel: 75,
    location: { latitude: 40.7128, longitude: -74.0060 },
    isAnomaly: false,
  },
  {
    timeGenerated: '2024-12-19T08:00:00Z',
    cowId: 'COW-001',
    sensorId: 'SENSOR-001',
    eatDuration: 51, // minutes
    eatSpeed: 5.1, // kg/hour
    anomalyScore: 0.05,
    temperature: 38.6,
    heartRate: 74,
    activityLevel: 82,
    location: { latitude: 40.7129, longitude: -74.0061 },
    isAnomaly: false,
  },
  {
    timeGenerated: '2024-12-19T10:00:00Z',
    cowId: 'COW-001',
    sensorId: 'SENSOR-001',
    eatDuration: 68, // minutes
    eatSpeed: 6.8, // kg/hour
    anomalyScore: 0.15,
    temperature: 38.7,
    heartRate: 76,
    activityLevel: 88,
    location: { latitude: 40.7130, longitude: -74.0062 },
    isAnomaly: false,
  },
  {
    timeGenerated: '2024-12-19T12:00:00Z',
    cowId: 'COW-001',
    sensorId: 'SENSOR-001',
    eatDuration: 85, // minutes
    eatSpeed: 8.5, // kg/hour
    anomalyScore: 0.3,
    temperature: 38.8,
    heartRate: 78,
    activityLevel: 90,
    location: { latitude: 40.7131, longitude: -74.0063 },
    isAnomaly: false,
  },
  {
    timeGenerated: '2024-12-19T14:00:00Z',
    cowId: 'COW-001',
    sensorId: 'SENSOR-001',
    eatDuration: 72, // minutes
    eatSpeed: 7.2, // kg/hour
    anomalyScore: 0.2,
    temperature: 38.6,
    heartRate: 75,
    activityLevel: 85,
    location: { latitude: 40.7132, longitude: -74.0064 },
    isAnomaly: false,
  },
  {
    timeGenerated: '2024-12-19T16:00:00Z',
    cowId: 'COW-001',
    sensorId: 'SENSOR-001',
    eatDuration: 69, // minutes
    eatSpeed: 6.9, // kg/hour
    anomalyScore: 0.12,
    temperature: 38.5,
    heartRate: 73,
    activityLevel: 80,
    location: { latitude: 40.7133, longitude: -74.0065 },
    isAnomaly: false,
  },
  {
    timeGenerated: '2024-12-19T18:00:00Z',
    cowId: 'COW-001',
    sensorId: 'SENSOR-001',
    eatDuration: 63, // minutes
    eatSpeed: 6.3, // kg/hour
    anomalyScore: 0.08,
    temperature: 38.4,
    heartRate: 71,
    activityLevel: 78,
    location: { latitude: 40.7134, longitude: -74.0066 },
    isAnomaly: false,
  },

  // COW-002 data with anomalies
  {
    timeGenerated: '2024-12-19T16:00:00Z',
    cowId: 'COW-002',
    sensorId: 'SENSOR-001',
    eatDuration: 21, // minutes - low
    eatSpeed: 2.1, // kg/hour - low
    anomalyScore: 0.85, // high anomaly score
    temperature: 39.2, // slightly elevated
    heartRate: 85, // elevated
    activityLevel: 45, // low activity
    location: { latitude: 40.7135, longitude: -74.0067 },
    isAnomaly: true,
  },
  {
    timeGenerated: '2024-12-19T18:00:00Z',
    cowId: 'COW-002',
    sensorId: 'SENSOR-001',
    eatDuration: 46, // minutes
    eatSpeed: 4.6, // kg/hour
    anomalyScore: 0.3,
    temperature: 38.9,
    heartRate: 78,
    activityLevel: 65,
    location: { latitude: 40.7136, longitude: -74.0068 },
    isAnomaly: false,
  },

  // COW-003 data with high consumption
  {
    timeGenerated: '2024-12-19T18:00:00Z',
    cowId: 'COW-003',
    sensorId: 'SENSOR-001',
    eatDuration: 118, // minutes - high
    eatSpeed: 11.8, // kg/hour - high
    anomalyScore: 0.75, // high anomaly score for overconsumption
    temperature: 38.3,
    heartRate: 68,
    activityLevel: 95, // high activity
    location: { latitude: 40.7137, longitude: -74.0069 },
    isAnomaly: true,
  },
];

// Mock AI models (Model AI table)
export const mockModels: ModelAI[] = [
  {
    modelId: 'MODEL-001',
    cowId: 'COW-001',
    model: 'FeedIntakePrediction_v2.1',
    accuracy: 0.94,
    lastTrained: '2024-12-15T10:00:00Z',
    status: 'active',
  },
  {
    modelId: 'MODEL-002',
    cowId: 'COW-002',
    model: 'HealthAnomalyDetection_v1.8',
    accuracy: 0.91,
    lastTrained: '2024-12-18T14:30:00Z',
    status: 'active',
  },
  {
    modelId: 'MODEL-003',
    cowId: 'COW-003',
    model: 'FeedIntakePrediction_v2.1',
    accuracy: 0.96,
    lastTrained: '2024-12-15T10:00:00Z',
    status: 'active',
  },
];

// Enhanced alerts matching ERD structure
export const mockAlerts: Alert[] = [
  {
    id: '1',
    cowId: 'COW-002',
    type: 'feeding',
    severity: 'high',
    message: 'COW-002 (Daisy): Konsumsi pakan rendah terdeteksi (2.1 kg/jam, durasi 21 menit)',
    isResolved: false,
    createdAt: '2024-12-19T16:30:00Z',
  },
  {
    id: '2',
    cowId: 'COW-003',
    type: 'feeding',
    severity: 'medium',
    message: 'COW-003 (Molly): Konsumsi berlebih terdeteksi (11.8 kg/jam, durasi 118 menit)',
    isResolved: false,
    createdAt: '2024-12-19T18:00:00Z',
  },
  {
    id: '3',
    cowId: 'COW-001',
    type: 'monitoring',
    severity: 'low',
    message: 'COW-001 (Bella): Pola makan normal, semua sensor berfungsi',
    isResolved: true,
    createdAt: '2024-12-19T18:30:00Z',
  },
  {
    id: '4',
    cowId: 'COW-002',
    type: 'health',
    severity: 'medium',
    message: 'COW-002 (Daisy): Sensor aktivitas menunjukkan penurunan gerakan (45% aktivitas)',
    isResolved: false,
    createdAt: '2024-12-19T15:45:00Z',
  },
  {
    id: '5',
    cowId: 'COW-003',
    type: 'monitoring',
    severity: 'low',
    message: 'COW-003 (Molly): Waktu makan teratur, tidak ada anomali',
    isResolved: true,
    createdAt: '2024-12-19T14:20:00Z',
  },
  {
    id: '6',
    cowId: 'COW-001',
    type: 'health',
    severity: 'medium',
    message: 'COW-001 (Bella): Deteksi pola makan tidak teratur pada pagi hari',
    isResolved: false,
    createdAt: '2024-12-19T08:15:00Z',
  },
  {
    id: '7',
    cowId: '',
    type: 'system',
    severity: 'low',
    message: 'Sistem: Backup data harian berhasil disimpan',
    isResolved: true,
    createdAt: '2024-12-19T06:00:00Z',
  },
  {
    id: '8',
    cowId: 'COW-002',
    type: 'health',
    severity: 'low',
    message: 'COW-002 (Daisy): Pemberian suplemen vitamin berhasil dicatat',
    isResolved: true,
    createdAt: '2024-12-19T12:30:00Z',
  },
];

// Feed intake data structure for charts (derived from Clean Data)
export const cattleFeedData = {
  'COW-001': {
    hourlyIntake: [
      { date: '06:00', value: 4.2, duration: 42, isAnomaly: false },
      { date: '08:00', value: 5.1, duration: 51, isAnomaly: false },
      { date: '10:00', value: 6.8, duration: 68, isAnomaly: false },
      { date: '12:00', value: 8.5, duration: 85, isAnomaly: false },
      { date: '14:00', value: 7.2, duration: 72, isAnomaly: false },
      { date: '16:00', value: 6.9, duration: 69, isAnomaly: false },
      { date: '18:00', value: 6.3, duration: 63, isAnomaly: false },
    ],
    cumulativeIntake: [
      { date: '06:00', value: 4.2, isAnomaly: false },
      { date: '08:00', value: 9.3, isAnomaly: false },
      { date: '10:00', value: 16.1, isAnomaly: false },
      { date: '12:00', value: 24.6, isAnomaly: false },
      { date: '14:00', value: 31.8, isAnomaly: false },
      { date: '16:00', value: 38.7, isAnomaly: false },
      { date: '18:00', value: 45.0, isAnomaly: false },
    ]
  },
  'COW-002': {
    hourlyIntake: [
      { date: '06:00', value: 3.8, duration: 38, isAnomaly: false },
      { date: '08:00', value: 4.2, duration: 42, isAnomaly: false },
      { date: '10:00', value: 3.9, duration: 39, isAnomaly: false },
      { date: '12:00', value: 5.1, duration: 51, isAnomaly: false },
      { date: '14:00', value: 4.8, duration: 48, isAnomaly: false },
      { date: '16:00', value: 2.1, duration: 21, isAnomaly: true },
      { date: '18:00', value: 4.6, duration: 46, isAnomaly: false },
    ],
    cumulativeIntake: [
      { date: '06:00', value: 3.8, isAnomaly: false },
      { date: '08:00', value: 8.0, isAnomaly: false },
      { date: '10:00', value: 11.9, isAnomaly: false },
      { date: '12:00', value: 17.0, isAnomaly: false },
      { date: '14:00', value: 21.8, isAnomaly: false },
      { date: '16:00', value: 23.9, isAnomaly: true },
      { date: '18:00', value: 28.5, isAnomaly: false },
    ]
  },
  'COW-003': {
    hourlyIntake: [
      { date: '06:00', value: 5.2, duration: 52, isAnomaly: false },
      { date: '08:00', value: 6.8, duration: 68, isAnomaly: false },
      { date: '10:00', value: 7.9, duration: 79, isAnomaly: false },
      { date: '12:00', value: 8.5, duration: 85, isAnomaly: false },
      { date: '14:00', value: 9.2, duration: 92, isAnomaly: false },
      { date: '16:00', value: 7.4, duration: 74, isAnomaly: false },
      { date: '18:00', value: 11.8, duration: 118, isAnomaly: true },
    ],
    cumulativeIntake: [
      { date: '06:00', value: 5.2, isAnomaly: false },
      { date: '08:00', value: 12.0, isAnomaly: false },
      { date: '10:00', value: 19.9, isAnomaly: false },
      { date: '12:00', value: 28.4, isAnomaly: false },
      { date: '14:00', value: 37.6, isAnomaly: false },
      { date: '16:00', value: 45.0, isAnomaly: false },
      { date: '18:00', value: 56.8, isAnomaly: true },
    ]
  }
};

// Enhanced cattle status with ERD-compliant data
export const mockCattleStatus: CattleStatus[] = mockCattle.map(cattle => {
  const lastReading = mockSensorReadings
    .filter(reading => reading.cowId === cattle.cowId)
    .sort((a, b) => new Date(b.timeGenerated).getTime() - new Date(a.timeGenerated).getTime())[0];
  
  const cattleAlerts = mockAlerts.filter(alert => alert.cowId === cattle.cowId && !alert.isResolved);
  
  // Calculate average values from readings
  const cattleReadings = mockSensorReadings.filter(reading => reading.cowId === cattle.cowId);
  const avgEatDuration = cattleReadings.reduce((sum, r) => sum + r.eatDuration, 0) / cattleReadings.length || 0;
  const avgEatSpeed = cattleReadings.reduce((sum, r) => sum + r.eatSpeed, 0) / cattleReadings.length || 0;
  const avgAnomalyScore = cattleReadings.reduce((sum, r) => sum + r.anomalyScore, 0) / cattleReadings.length || 0;
  
  let currentHealth: CattleStatus['currentHealth'] = 'good';
  let feedingPattern = 'Normal';
  
  if (cattle.status === 'sick') {
    currentHealth = 'poor';
    if (avgEatSpeed < 3) feedingPattern = 'Rendah';
  } else if (avgEatSpeed > 10) {
    currentHealth = 'fair';
    feedingPattern = 'Tinggi';
  } else if (avgEatSpeed > 8) {
    currentHealth = 'excellent';
    feedingPattern = 'Normal';
  }

  return {
    cowId: cattle.cowId,
    cattle,
    currentHealth,
    lastReading: lastReading || {
      timeGenerated: new Date().toISOString(),
      cowId: cattle.cowId,
      sensorId: 'SENSOR-001',
      eatDuration: 60,
      eatSpeed: 6.0,
      anomalyScore: 0.1,
      temperature: 38.5,
      heartRate: 72,
      activityLevel: 75,
      location: { latitude: 40.7128, longitude: -74.0060 },
    },
    alerts: cattleAlerts,
    avgEatDuration: Math.round(avgEatDuration),
    avgEatSpeed: Math.round(avgEatSpeed * 10) / 10,
    anomalyScore: Math.round(avgAnomalyScore * 100) / 100,
    feedingPattern,
  };
});

// Mock login function
export function mockLogin(email: string, password: string): Promise<{ user: User; token: string }> {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      const user = mockUsers.find(u => u.email === email);
      if (user && password === 'password') {
        resolve({
          user,
          token: 'mock-jwt-token',
        });
      } else {
        reject(new Error('Invalid credentials'));
      }
    }, 1000);
  });
}

// Mock register function
export function mockRegister(userData: { name: string; email: string; password: string }): Promise<{ user: User; token: string }> {
  return new Promise((resolve, reject) => {
    setTimeout(() => {
      const existingUser = mockUsers.find(u => u.email === userData.email);
      if (existingUser) {
        reject(new Error('User already exists'));
      } else {
        const newUser: User = {
          farmerId: generateId(),
          email: userData.email,
          name: userData.name,
          role: 'user',
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };
        mockUsers.push(newUser);
        resolve({
          user: newUser,
          token: 'mock-jwt-token',
        });
      }
    }, 1000);
  });
}