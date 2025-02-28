import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const flaskApiUrl = process.env.FLASK_API_URL || 'http://127.0.0.1:5328';
  console.log(`[DEBUG] Using Flask API URL: ${flaskApiUrl}`);
  
  try {
    const body = await request.json();
    console.log("[DEBUG] Request body:", JSON.stringify(body));
    
    console.log(`[DEBUG] Attempting to fetch from: ${flaskApiUrl}/api/post_info`);
    const flaskResponse = await fetch(`${flaskApiUrl}/api/post_info`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      cache: 'no-store',
    });

    console.log(`[DEBUG] Flask response status: ${flaskResponse.status}`);
    
    if (!flaskResponse.ok) {
      const errorText = await flaskResponse.text();
      console.error(`Flask API returned error (${flaskResponse.status}):`, errorText);
      throw new Error(`Flask API error: ${flaskResponse.status} - ${errorText}`);
    }

    const data = await flaskResponse.json();
    console.log("[DEBUG] Successfully got data from Flask");
    return NextResponse.json(data);
  } catch (error) {
    console.error('[DEBUG] Detailed fetch error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'An unknown error occurred' },
      { status: 500 }
    );
  }
} 