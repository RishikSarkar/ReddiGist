import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    // Log the Flask API URL for debugging
    console.log("Attempting to connect to Flask API at:", process.env.FLASK_API_URL || 'http://127.0.0.1:5328');
    
    const flaskResponse = await fetch(`${process.env.FLASK_API_URL || 'http://127.0.0.1:5328'}/api/top_phrases`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      // Add these options to improve connection reliability
      cache: 'no-store',
    });

    if (!flaskResponse.ok) {
      const errorText = await flaskResponse.text();
      console.error(`Flask API returned error (${flaskResponse.status}):`, errorText);
      throw new Error(`Flask API error: ${flaskResponse.status}`);
    }

    const data = await flaskResponse.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error forwarding to Flask API:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'An unknown error occurred' },
      { status: 500 }
    );
  }
} 