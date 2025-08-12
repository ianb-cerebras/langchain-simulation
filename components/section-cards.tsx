// Removed unused imports
import {
  Card,
  CardAction,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

interface SectionCardsProps {
  insights?: {
    keyInsights?: string;
    observations?: string;
    takeaways?: string;
  } | null;
}

export function SectionCards({ insights }: SectionCardsProps) {
  function takeFirstSentences(text: string | undefined | null, limit: number = 3): string {
    const value = (text ?? "").toString().trim()
    if (!value) return ""
    // Extract sentences keeping punctuation. Fallback to whole string if regex fails
    const sentences = value.match(/[^.!?\n]+[.!?]+|[^.!?\n]+$/g) || [value]
    const clipped = sentences.slice(0, limit).join(" ").trim()
    return clipped
  }

  const defaultKey = "Users seemed generally unhappy with an orange Coca Cola rebrand"
  const defaultObs = "Focus groups cited confusion and a loss of brand trust when Coca-Cola shifted to orange packaging."
  const defaultTake = "Consumers still prefer the classic red branding; radical color changes risk eroding long-standing brand equity."

  const keyInsights = takeFirstSentences(insights?.keyInsights ?? defaultKey, 3) || defaultKey
  const observations = takeFirstSentences(insights?.observations ?? defaultObs, 3) || defaultObs
  const takeaways = takeFirstSentences(insights?.takeaways ?? defaultTake, 3) || defaultTake

  return (
    <div className="grid w-full gap-6 [grid-template-columns:repeat(auto-fit,minmax(260px,1fr))] *:data-[slot=card]:from-primary/5 *:data-[slot=card]:to-card dark:*:data-[slot=card]:bg-card *:data-[slot=card]:bg-gradient-to-t *:data-[slot=card]:shadow-xs">
      <Card className="@container/card">
        <CardHeader>
          <CardDescription>Key Insights</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
          </CardTitle>
          <CardAction>
          </CardAction>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="text-muted-foreground">
            {keyInsights}
          </div>
        </CardFooter>
      </Card>
      <Card className="@container/card">
        <CardHeader>
          <CardDescription>Points of Observation</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            
          </CardTitle>
          <CardAction>
          </CardAction>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            
          </div>
          <div className="text-muted-foreground">
            {observations}
          </div>
        </CardFooter>
      </Card>
      <Card className="@container/card">
        <CardHeader>
          <CardDescription>Big Takeaways</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            
          </CardTitle>
          <CardAction>
          </CardAction>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            
          </div>
          <div className="text-muted-foreground">
            {takeaways}
          </div>
        </CardFooter>
      </Card>
    </div>
  )
}
