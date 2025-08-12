import { NextResponse } from "next/server";

// Ensure Node.js runtime so we can use the filesystem
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
import { join } from "path";
import { readFile } from "fs/promises";

export async function GET() {
  try {
    // Prefer /tmp on serverless (Vercel) if present, else fall back to project root
    const isVercel = !!process.env.VERCEL;
    const tmpPath = "/tmp/uxr-result.json";
    const localPath = join(process.cwd(), "uxr-result.json");

    let data: string | null = null;

    if (isVercel) {
      try {
        data = await readFile(tmpPath, "utf-8");
      } catch {
        // fall through to localPath
      }
    }

    if (!data) {
      data = await readFile(localPath, "utf-8");
    }

    const res = NextResponse.json(JSON.parse(data));
    res.headers.set("Cache-Control", "no-store");
    return res;
  } catch {
    return NextResponse.json({ error: "No results yet" }, { status: 404 });
  }
}
