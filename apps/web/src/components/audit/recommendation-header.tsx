import { cn } from "cn"
import { CircleCheckIcon, CircleXIcon, TriangleAlertIcon } from "@/components/icons"
import type { AIDecision, ClaimPriority } from "@/lib/types/api"
import { formatPercent, toTitleCase } from "@/lib/format"
import { PriorityBadge } from "@/components/claims/status-badge"

const DECISION_CONFIG: Record<
  AIDecision,
  { label: string; icon: typeof CircleCheckIcon; tone: string; bar: string }
> = {
  approve: {
    label: "Recommend approval",
    icon: CircleCheckIcon,
    tone: "bg-success/10 text-success",
    bar: "bg-success",
  },
  reject: {
    label: "Recommend rejection",
    icon: CircleXIcon,
    tone: "bg-destructive/10 text-destructive",
    bar: "bg-destructive",
  },
  review: {
    label: "Needs manual review",
    icon: TriangleAlertIcon,
    tone: "bg-warning/10 text-warning",
    bar: "bg-warning",
  },
}

interface RecommendationHeaderProps {
  decision: AIDecision | null
  confidence: number | null
  priority: ClaimPriority | null
  className?: string
}

export function RecommendationHeader({
  decision,
  confidence,
  priority,
  className,
}: RecommendationHeaderProps) {
  const config = decision ? DECISION_CONFIG[decision] : null
  const Icon = config?.icon ?? TriangleAlertIcon

  return (
    <div className={cn("flex flex-col gap-4 rounded-2xl p-5 ring-1 ring-foreground/10", className)}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              "flex size-10 shrink-0 items-center justify-center rounded-full",
              config?.tone ?? "bg-muted text-muted-foreground"
            )}
          >
            <Icon className="size-5" />
          </div>
          <div>
            <p className="font-heading text-base font-semibold">
              {config?.label ?? "No recommendation yet"}
            </p>
            {priority && (
              <div className="mt-1">
                <PriorityBadge priority={priority} />
              </div>
            )}
          </div>
        </div>

        {confidence !== null && (
          <div className="text-right">
            <p className="font-mono text-2xl leading-none font-semibold tabular-nums">
              {formatPercent(confidence)}
            </p>
            <p className="text-xs text-muted-foreground">confidence</p>
          </div>
        )}
      </div>

      {confidence !== null && (
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
          <div
            className={cn("h-full rounded-full transition-all", config?.bar ?? "bg-primary")}
            style={{ width: `${Math.round(confidence * 100)}%` }}
          />
        </div>
      )}
    </div>
  )
}

export function decisionLabel(decision: string | null): string {
  return decision ? toTitleCase(decision) : "Pending"
}
