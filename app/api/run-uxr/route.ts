import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import { join } from "path";

export async function POST(req: NextRequest) {
  const { question, audience, numInterviews } = await req.json();
  const scriptPath = join(process.cwd(), "enhanced_uxr.py");

  // Save config locally (simple JSON next to script)
  const fs = await import("fs/promises");
  await fs.writeFile(
    join(process.cwd(), "uxr-config.json"),
    JSON.stringify({ question, audience, numInterviews }, null, 2)
  );

  return new Promise<NextResponse>((resolve) => {
    const python = spawn("python3", [scriptPath], {
      env: {
        ...process.env,
        UXR_QUESTION: question ?? "",
        UXR_AUDIENCE: audience ?? "",
        UXR_NUM_INTERVIEWS: String(numInterviews ?? ""),
        CEREBRAS_API_KEY: process.env.CEREBRAS_API_KEY ?? "",
      },
    });

    let stdout = "";
    let stderr = "";

    python.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    python.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    python.on("close", async (code) => {
      if (code === 0) {
        // save result json for dashboard
        try {
          // Extract JSON from stdout - it should be the first complete JSON object
          const lines = stdout.split("\n");
          let jsonContent = "";
          let braceCount = 0;
          let startedJson = false;
          
          for (const line of lines) {
            if (line.trim().startsWith("{") && !startedJson) {
              startedJson = true;
              jsonContent = line;
              braceCount = (line.match(/\{/g) || []).length - (line.match(/\}/g) || []).length;
            } else if (startedJson) {
              jsonContent += "\n" + line;
              braceCount += (line.match(/\{/g) || []).length - (line.match(/\}/g) || []).length;
              
              if (braceCount === 0) {
                break; // Complete JSON object found
              }
            }
          }
          
          if (jsonContent && startedJson) {
            const parsed = JSON.parse(jsonContent);
            await fs.writeFile(join(process.cwd(), "uxr-result.json"), JSON.stringify(parsed, null, 2));
            console.log("✅ Saved results:", parsed);
            resolve(NextResponse.json({ success: true, output: stdout, data: parsed }));
          } else {
            console.log("⚠️ No JSON found in output:", stdout);
            resolve(NextResponse.json({ success: true, output: stdout }));
          }
        } catch (e) {
          console.error("❌ Failed to parse JSON:", e);
          console.log("Raw stdout:", stdout);
          resolve(NextResponse.json({ success: true, output: stdout }));
        }
      } else {
        resolve(
          NextResponse.json(
            { success: false, error: stderr || `Process exited with code ${code}` },
            { status: 500 }
          )
        );
      }
    });
  });
}
