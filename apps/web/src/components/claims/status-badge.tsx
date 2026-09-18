import { cn } from "cn"
import { toTitleCase } from "@/lib/format"

type Tone = "success" | "warning" | "destructive" | "info" | "muted"

const TONE_CLASSES: Record<Tone, string> = {
  success: "bg-success/10 text-success dark:bg-success/20",
  warning: "bg-warning/10 text-warning dark:bg-warning/20",
  destructive: "bg-destructive/10 text-destructive dark:bg-destructive/20",
  info: "bg-info/10 text-info dark:bg-info/20",
  muted: "bg-muted text-muted-foreground",
}

function Pill({ tone, children, className }: { tone: Tone; children: React.ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex h-5 w-fit shrink-0 items-center justify-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap",
        TONE_CLASSES[tone],
        className
      )}
    >
      {children}
    </span>
  )
}

const CLAIM_STATUS_TONE: Record<string, Tone> = {
  draft: "muted",
  submitted: "info",
  in_audit: "warning",
  approved: "success",
  rejected: "destructive",
  needs_revision: "warning",
}

export function ClaimStatusBadge({ status }: { status: string }) {
  const tone = CLAIM_STATUS_TONE[status] ?? "muted"
  return <Pill tone={tone}>{toTitleCase(status)}</Pill>
}

const PRIORITY_TONE: Record<string, Tone> = {
  low: "muted",
  medium: "info",
  high: "warning",
  urgent: "destructive",
}

export function PriorityBadge({ priority }: { priority: string }) {
  const tone = PRIORITY_TONE[priority] ?? "muted"
  return <Pill tone={tone}>{toTitleCase(priority)}</Pill>
}

const AI_RUN_STATUS_TONE: Record<string, Tone> = {
  pending: "muted",
  running: "info",
  completed: "success",
  failed: "destructive",
}

export function AiRunStatusBadge({ status }: { status: string }) {
  const tone = AI_RUN_STATUS_TONE[status] ?? "muted"
  return <Pill tone={tone}>{toTitleCase(status)}</Pill>
}

const AI_DECISION_LABEL: Record<string, string> = {
  approve: "Approve",
  reject: "Reject",
  review: "Review",
}

const AI_DECISION_TONE: Record<string, Tone> = {
  approve: "success",
  reject: "destructive",
  review: "warning",
}

export function AiDecisionBadge({ decision }: { decision: string | null }) {
  if (!decision) return <Pill tone="muted">No recommendation</Pill>
  const tone = AI_DECISION_TONE[decision] ?? "muted"
  return <Pill tone={tone}>{AI_DECISION_LABEL[decision] ?? toTitleCase(decision)}</Pill>
}

const SEVERITY_TONE: Record<string, Tone> = {
  blocking: "destructive",
  warning: "warning",
  info: "info",
}

export function SeverityBadge({ severity }: { severity: string }) {
  const tone = SEVERITY_TONE[severity.toLowerCase()] ?? "muted"
  return <Pill tone={tone}>{toTitleCase(severity)}</Pill>
}

const CHECK_STATUS_TONE: Record<string, Tone> = {
  passed: "success",
  failed: "destructive",
  not_applicable: "muted",
}

export function CheckStatusBadge({ status }: { status: string }) {
  const tone = CHECK_STATUS_TONE[status] ?? "muted"
  return <Pill tone={tone}>{toTitleCase(status)}</Pill>
}
