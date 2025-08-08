import { NextResponse } from "next/server";
import { join } from "path";
import { readFile } from "fs/promises";

export async function GET() {
  try {
    const data = await readFile(join(process.cwd(), "uxr-result.json"), "utf-8");
    return NextResponse.json(JSON.parse(data));
  } catch {
    return NextResponse.json({ error: "No results yet" }, { status: 404 });
  }
}
