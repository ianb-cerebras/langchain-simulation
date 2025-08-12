"use client"

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";

export default function ConfigPage() {
  // Removed unused TextAreaStyle
  const [apiKey, setApiKey] = useState("");
  const [project, setProject] = useState("");
  const [numInterviews, setNumInterviews] = useState<number[]>([10]);
  const [cerebrasApiKey, setCerebrasApiKey] = useState("");
  const router = useRouter();

  // Load saved Cerebras API key from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem("CEREBRAS_API_KEY");
      if (saved) setCerebrasApiKey(saved);
    } catch {
      // ignore
    }
  }, []);

  // Persist Cerebras API key on change
  useEffect(() => {
    try {
      if (cerebrasApiKey) {
        localStorage.setItem("CEREBRAS_API_KEY", cerebrasApiKey);
      } else {
        localStorage.removeItem("CEREBRAS_API_KEY");
      }
    } catch {
      // ignore
    }
  }, [cerebrasApiKey]);

  async function handleSave() {
    // Placeholder: persist later
    console.log({ apiKey, project, numInterviews: numInterviews[0] });
    try {
      const res = await fetch("/api/run-uxr", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: apiKey,
          audience: project,
          numInterviews: numInterviews[0],
          cerebrasApiKey: cerebrasApiKey || undefined,
        }),
      });
      const data = await res.json();
      console.log(data);
      if (data.success) {
        try {
          if (data.data) {
            localStorage.setItem("UXR_LAST_RESULT", JSON.stringify(data.data));
          }
        } catch {}
        router.push("/dashboard");
      } else {
        alert("Error running simulation: " + (data.error ?? "unknown"));
      }
    } catch (err) {
      console.error(err);
      alert("Request failed");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <Card className="w-full max-w-md space-y-6 shadow-md">
        <CardHeader>
          <CardTitle className="text-xl">User Research Simulation</CardTitle>
          <CardDescription>Answer your big questions by simulating your UX research</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-6">
          {/* Cerebras API Key */}
          <div className="flex flex-col gap-2">
            <label className="block text-sm font-medium" htmlFor="cerebras-api-key">
              Cerebras API Key
            </label>
            <Input
              id="cerebras-api-key"
              type="password"
              placeholder="sk_cerebras_..."
              value={cerebrasApiKey}
              onChange={(e) => setCerebrasApiKey(e.target.value)}
              autoComplete="off"
              name="cerebras-api-key"
              className="bg-white dark:bg-input/30"
            />
          </div>

          {/* API Key */}
          <div className="flex flex-col gap-2">
            <label className="block text-sm font-medium" htmlFor="api-key">
              What question would you like to answer?
            </label>
            <Input
              id="api-key"
              placeholder="How would users feel about a pink iPhone?"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />
          </div>

          {/* Project Name */}
          <div className="flex flex-col gap-2">
            <label className="block text-sm font-medium" htmlFor="project-name">
              Target Audience
            </label>
            <Input
              id="project-name"
              placeholder="Gen Z"
              value={project}
              onChange={(e) => setProject(e.target.value)}
            />
          </div>

          {/* Slider */}
          <div className="flex flex-col gap-2">
            <label className="block text-sm font-medium" htmlFor="interviews">
              Number of Interviews: {numInterviews[0]}
            </label>
            <Slider
              id="interviews"
              min={1}
              max={50}
              value={numInterviews}
              onValueChange={setNumInterviews}
            />
          </div>
        </CardContent>
        <CardFooter className="pt-0">
          <Button className="w-full" onClick={handleSave}>
            Run Simulation
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}

