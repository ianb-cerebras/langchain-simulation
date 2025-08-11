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
            {insights?.keyInsights || "Users seemed generally unhappy with an orange Coca Cola rebrand"}
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
            {insights?.observations || "Focus groups cited confusion and a loss of brand trust when Coca-Cola shifted to orange packaging."}
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
            {insights?.takeaways || "Consumers still prefer the classic red branding; radical color changes risk eroding long-standing brand equity."}
          </div>
        </CardFooter>
      </Card>
    </div>
  )
}
