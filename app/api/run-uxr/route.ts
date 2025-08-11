import { NextRequest, NextResponse } from "next/server";

// Ensure Node.js runtime so we can use the filesystem
export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  try {
    const { question, audience, numInterviews, cerebrasApiKey } = await req.json();

    const flaskUrl = process.env.FLASK_URL;
    if (!flaskUrl) {
      return NextResponse.json(
        {
          success: false,
          error: "Missing FLASK_URL",
          hint: "Set FLASK_URL to your deployed Flask base URL (e.g. https://your-service.onrender.com)",
        },
        { status: 500 }
      );
    }

    const response = await fetch(`${flaskUrl}/api/run-uxr`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        audience,
        numInterviews: numInterviews || 5,
        numQuestions: 3,
        cerebrasApiKey,
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      return NextResponse.json(
        { success: false, error: error || "Flask backend error" },
        { status: response.status }
      );
    }

    const result = await response.json();

    // Save result locally for dashboard
    const fs = await import("fs/promises");
    const { join } = await import("path");

    // In Vercel/serverless environments, the filesystem is read-only except for /tmp
    const isVercel = !!process.env.VERCEL;
    const resultsPath = isVercel
      ? "/tmp/uxr-result.json"
      : join(process.cwd(), "uxr-result.json");

    if (result.data) {
      await fs.writeFile(resultsPath, JSON.stringify(result.data, null, 2));
      console.log(`✅ Saved UXR results to ${resultsPath}`);
    }
    
    return NextResponse.json(result);
  } catch (error) {
    console.error("Error calling Flask backend:", error);
    return NextResponse.json(
      { 
        success: false, 
        error: error instanceof Error ? error.message : "Failed to run UXR simulation",
        hint: "Make sure the Flask backend is running on port 5000"
      },
      { status: 500 }
    );
  }
}