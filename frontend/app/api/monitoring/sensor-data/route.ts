import { NextRequest, NextResponse } from 'next/server';
import { mockSensorReadings } from '@/lib/mock-data';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const cattleId = searchParams.get('cattleId');

    let readings = mockSensorReadings;
    
    if (cattleId) {
      readings = mockSensorReadings.filter(reading => reading.cowId === cattleId);
    }

    return NextResponse.json(readings, { status: 200 });
  } catch (error) {
    return NextResponse.json(
      { message: 'Failed to fetch sensor data' },
      { status: 500 }
    );
  }
}
