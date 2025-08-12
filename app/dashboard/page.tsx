"use client"


import { SectionCards } from "@/components/section-cards"
import { ChartAreaInteractive } from "@/components/chart-area-interactive"
import { DataTable } from "@/components/data-table"
import { useEffect, useState } from "react";

interface InsightResult {
  keyInsights: string;
  observations: string;
  takeaways: string;
  participants?: Array<{
    id: number;
    header: string;
    type: string;
    status: string;
    target: string;
    limit: string;
    interview?: {
      persona: unknown;
      responses: Array<{
        question: string;
        answer: string;
        is_followup?: boolean;
      }>;
    };
  }>;
  all_interviews?: Array<{
    persona: unknown;
    responses: Array<{
      question: string;
      answer: string;
      is_followup?: boolean;
    }>;
  }>;
}

export default function DashboardPage() {
  const [insights, setInsights] = useState<InsightResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetch("/api/uxr-result")
      .then((res) => res.ok ? res.json() : null)
      .then((data) => {
        if (data && (data.keyInsights || data.participants)) {
          setInsights(data);
          try { localStorage.setItem("UXR_LAST_RESULT", JSON.stringify(data)); } catch {}
        } else {
          // Try localStorage fallback
          try {
            const cached = localStorage.getItem("UXR_LAST_RESULT");
            if (cached) {
              const parsed = JSON.parse(cached);
              if (parsed && (parsed.keyInsights || parsed.participants)) {
                setInsights(parsed);
              }
            }
          } catch {}
        }
        setIsLoading(false);
      })
      .catch(() => {
        // On error, also try localStorage
        try {
          const cached = localStorage.getItem("UXR_LAST_RESULT");
          if (cached) {
            const parsed = JSON.parse(cached);
            if (parsed && (parsed.keyInsights || parsed.participants)) {
              setInsights(parsed);
            }
          }
        } catch {}
        setIsLoading(false);
      });
  }, []);

  // Fallback data when no simulation results exist
  const fallbackData = [
    {
      id: 1,
      header: "Ava Spencer",
      type: "Gen Z",
      status: "Curious, Social",
      target: "22",
      limit: "Student",
    },
    {
      id: 2,
      header: "Marcus Chen",
      type: "Gen Z",
      status: "Creative, Analytical", 
      target: "24",
      limit: "Designer",
    },
    {
      id: 3,
      header: "Zoe Martinez",
      type: "Gen Z",
      status: "Outgoing, Practical",
      target: "21",
      limit: "Barista",
    },
    {
      id: 4,
      header: "Jordan Kim",
      type: "Gen Z",
      status: "Logical, Detail-oriented",
      target: "23",
      limit: "Developer",
    },
    {
      id: 5,
      header: "Riley Thompson",
      type: "Gen Z",
      status: "Trendy, Expressive",
      target: "20",
      limit: "Influencer",
    },
  ];

  return (
    <div className="min-h-screen p-6">
      <h1 className="text-2xl font-bold mb-4">
        {insights ? "Simulation Results" : "Sample Dashboard"}
      </h1>
      
      {!insights && !isLoading && (
        <p className="text-muted-foreground mb-8">
          Run a simulation from the configuration page to see real results here.
        </p>
      )}

      {/* Stats Overview - now displays actual insights or fallbacks */}
      <SectionCards insights={insights} />

      {/* Visitors Chart */}
      <div className="mt-6 grid grid-cols-1 gap-6 @[1200px]/content:grid-cols-4">
        <ChartAreaInteractive simulationData={insights ?? undefined} />
      </div>

      {/* Simulated Participants Table */}
      <div className="mt-10">
        <h2 className="text-xl font-semibold mb-4">
          {insights ? "Simulated Participants" : "Sample Participants"}
        </h2>
        <DataTable data={insights?.participants || fallbackData} />
      </div>
    </div>
  )
}

