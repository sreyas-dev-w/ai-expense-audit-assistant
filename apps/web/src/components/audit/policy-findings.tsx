import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { FileTextIcon } from "@/components/icons"
import { SeverityBadge, CheckStatusBadge } from "@/components/claims/status-badge"
import { formatPercent, toTitleCase } from "@/lib/format"
import type { PolicyAgentOutput } from "@/lib/types/api"

const SEVERITY_ORDER: Record<string, number> = { blocking: 0, warning: 1, info: 2 }

export function PolicyFindings({ policy }: { policy: PolicyAgentOutput }) {
  const violations = [...policy.violations].sort(
    (a, b) => (SEVERITY_ORDER[a.severity] ?? 3) - (SEVERITY_ORDER[b.severity] ?? 3)
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Policy findings</span>
          <span className="text-xs font-normal text-muted-foreground">
            {toTitleCase(policy.decision)} · {formatPercent(policy.confidence)} confidence
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {policy.summary && <p className="text-sm text-muted-foreground">{policy.summary}</p>}

        {violations.length > 0 && (
          <div className="flex flex-col divide-y">
            {violations.map((violation, i) => (
              <div key={i} className="flex flex-col gap-1.5 py-3 first:pt-0 last:pb-0">
                <div className="flex items-center gap-2">
                  <SeverityBadge severity={violation.severity} />
                  <span className="text-sm font-medium">{violation.description}</span>
                </div>
                {violation.detail && (
                  <p className="text-sm text-muted-foreground">{violation.detail}</p>
                )}
                {violation.policy_reference && (
                  <div className="flex items-center gap-2 self-start rounded-md border border-border/60 bg-muted/40 px-2.5 py-1.5">
                    <FileTextIcon className="size-3.5 shrink-0 text-muted-foreground" />
                    <span className="font-mono text-xs text-muted-foreground">
                      {violation.policy_reference}
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {policy.checks.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {policy.checks.map((check, i) => (
              <div
                key={i}
                className="flex items-center gap-1.5 rounded-lg bg-muted/50 px-2.5 py-1 text-xs"
              >
                <CheckStatusBadge status={check.status} />
                <span>{check.check_name}</span>
              </div>
            ))}
          </div>
        )}

        {violations.length === 0 && policy.checks.length === 0 && (
          <p className="text-sm text-muted-foreground">No policy violations were found.</p>
        )}
      </CardContent>
    </Card>
  )
}
