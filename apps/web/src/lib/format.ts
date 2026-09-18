import type { PolicyAgentOutput, ValidationAgentOutput } from "@/lib/types/api"

export function formatMoney(amount: string | number | null | undefined, currency = "INR"): string {
  if (amount === null || amount === undefined) return "-"
  const value = typeof amount === "string" ? Number(amount) : amount
  if (Number.isNaN(value)) return "-"
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(value)
  } catch {
    return `${currency} ${value.toFixed(2)}`
  }
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "-"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(date)
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "-"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date)
}

export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "-"
  return `${Math.round(value * 100)}%`
}

export function toTitleCase(value: string | null | undefined): string {
  if (!value) return "-"
  return value
    .toLowerCase()
    .split(/[_\s]+/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ")
}

/**
 * `notes` on `AuditResult` / `ClaimAuditUpdate` is a newline-joined summary
 * (`AI recommendation for claim N: ...` / `Reasons: ...` / `Warnings: ...`).
 * Split it into lines rather than rendering it as one blob.
 */
export function splitNotes(notes: string | null | undefined): string[] {
  if (!notes) return []
  return notes.split("\n").filter(Boolean)
}

/**
 * `agent_response.policy_response` / `validation_response` are written by two
 * different code paths with different shapes: the audit graph writes the full
 * envelope `{status, output, error}`, while `/validation/evaluate` writes the
 * bare output. Read defensively.
 */
export function unwrapAgentPayload<T>(
  payload: Record<string, unknown> | null | undefined
): T | null {
  if (!payload) return null
  if ("output" in payload) {
    return (payload.output as T | null) ?? null
  }
  return payload as T
}

export function unwrapPolicyOutput(
  payload: Record<string, unknown> | null | undefined
): PolicyAgentOutput | null {
  return unwrapAgentPayload<PolicyAgentOutput>(payload)
}

export function unwrapValidationOutput(
  payload: Record<string, unknown> | null | undefined
): ValidationAgentOutput | null {
  return unwrapAgentPayload<ValidationAgentOutput>(payload)
}
