import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const { question, audience, numInterviews } = await req.json();
    
    // Call Flask backend
    const flaskUrl = process.env.FLASK_URL || "http://localhost:5000";
    const response = await fetch(`${flaskUrl}/api/run-uxr`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question,
        audience,
        numInterviews: numInterviews || 5,
        numQuestions: 3  // Default to 3 questions
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(
        { success: false, error: error.error || "Flask backend error" },
        { status: response.status }
      );
    }

    const result = await response.json();
    
    // Save result locally for dashboard
    const fs = await import("fs/promises");
    const { join } = await import("path");
    
    if (result.data) {
      await fs.writeFile(
        join(process.cwd(), "uxr-result.json"),
        JSON.stringify(result.data, null, 2)
      );
      console.log("✅ Saved UXR results");
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