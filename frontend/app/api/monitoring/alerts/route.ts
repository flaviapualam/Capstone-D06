import { NextResponse } from 'next/server';
import { mockAlerts } from '@/lib/mock-data';

export async function GET() {
  try {
    return NextResponse.json(mockAlerts, { status: 200 });
  } catch (error) {
    return NextResponse.json(
      { message: 'Failed to fetch alerts' },
      { status: 500 }
    );
  }
}
