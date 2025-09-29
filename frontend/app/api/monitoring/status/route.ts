import { NextResponse } from 'next/server';
import { mockCattleStatus } from '@/lib/mock-data';

export async function GET() {
  try {
    return NextResponse.json(mockCattleStatus, { status: 200 });
  } catch (error) {
    return NextResponse.json(
      { message: 'Failed to fetch cattle status' },
      { status: 500 }
    );
  }
}
