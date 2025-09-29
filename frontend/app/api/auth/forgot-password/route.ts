import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { email } = await request.json();

    if (!email) {
      return NextResponse.json(
        { message: 'Email is required' },
        { status: 400 }
      );
    }

    // Mock forgot password - in real app, send email
    return NextResponse.json(
      { message: 'Password reset instructions sent to your email' },
      { status: 200 }
    );
  } catch (error) {
    return NextResponse.json(
      { message: 'Failed to process forgot password request' },
      { status: 500 }
    );
  }
}
