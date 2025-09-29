import { NextRequest, NextResponse } from 'next/server';
import { mockCattle } from '@/lib/mock-data';
import { generateId } from '@/lib/utils';
import { Cattle } from '@/types';

export async function GET() {
  try {
    return NextResponse.json(mockCattle, { status: 200 });
  } catch (error) {
    return NextResponse.json(
      { message: 'Failed to fetch cattle' },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const cattleData = await request.json();
    
    const { name, breed, age, weight, status, notes } = cattleData;

    if (!name || !breed || !age || !weight || !status) {
      return NextResponse.json(
        { message: 'Missing required fields' },
        { status: 400 }
      );
    }

    const newCattle: Cattle = {
      cowId: generateId(),
      farmerId: 'FARMER-001', // Default farmer
      name,
      breed,
      age: Number(age),
      weight: Number(weight),
      status,
      notes: notes || '',
      lastCheckup: new Date().toISOString(),
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    mockCattle.push(newCattle);

    return NextResponse.json(newCattle, { status: 201 });
  } catch (error) {
    return NextResponse.json(
      { message: 'Failed to create cattle record' },
      { status: 500 }
    );
  }
}