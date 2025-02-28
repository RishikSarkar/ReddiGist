import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const isProduction = process.env.NODE_ENV === 'production';
  
  try {
    const body = await request.json();
    
    if (isProduction) {
      // In production, return a simplified response
      return NextResponse.json({
        phrases: [
          { phrase: "This is a simplified production response", score: "1.00", upvotes: 1 },
          { phrase: "Please deploy a Flask API for full functionality", score: "0.75", upvotes: 1 },
        ],
        topic: "Simplified Response",
        note: "For full functionality, deploy a Flask API and set FLASK_API_URL"
      });
    } else {
      // In development, forward to Flask
      const flaskApiUrl = process.env.FLASK_API_URL || 'http://127.0.0.1:5328';
      console.log("Attempting to connect to Flask API at:", flaskApiUrl);
      
      const flaskResponse = await fetch(`${flaskApiUrl}/api/top_phrases`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
        cache: 'no-store',
      });

      if (!flaskResponse.ok) {
        const errorText = await flaskResponse.text();
        console.error(`Flask API returned error (${flaskResponse.status}):`, errorText);
        throw new Error(`Flask API error: ${flaskResponse.status}`);
      }

      const data = await flaskResponse.json();
      return NextResponse.json(data);
    }
  } catch (error) {
    console.error('Error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'An unknown error occurred' },
      { status: 500 }
    );
  }
} 