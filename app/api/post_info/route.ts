import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const isProduction = process.env.NODE_ENV === 'production';
  
  try {
    const body = await request.json();
    
    if (isProduction) {
      try {
        const url = body.url;
        if (!url) {
          return NextResponse.json({ error: "URL is required" }, { status: 400 });
        }
        
        const match = url.match(/\/comments\/([^/]+)\//);
        const submissionId = match ? match[1] : null;
        
        if (!submissionId) {
          return NextResponse.json({ error: "Invalid Reddit URL" }, { status: 400 });
        }
        
        return NextResponse.json({
          title: "Post from " + url,
          numComments: 0,
          note: "Simplified response in production mode"
        });
      } catch (error) {
        console.error("Error processing Reddit post:", error);
        return NextResponse.json({ 
          error: error instanceof Error ? error.message : "Failed to process Reddit post" 
        }, { status: 500 });
      }
    } else {
      const flaskApiUrl = process.env.FLASK_API_URL || 'http://127.0.0.1:5328';
      console.log(`[DEBUG] Using Flask API URL: ${flaskApiUrl}`);
      
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
    }
  } catch (error) {
    console.error('[DEBUG] Detailed fetch error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'An unknown error occurred' },
      { status: 500 }
    );
  }
} 