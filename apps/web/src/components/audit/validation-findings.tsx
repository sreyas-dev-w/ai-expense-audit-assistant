import { CopyIcon } from "@/components/icons"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { SeverityBadge, CheckStatusBadge } from "@/components/claims/status-badge"
import { formatMoney, formatPercent, toTitleCase } from "@/lib/format"
import type { ValidationAgentOutput } from "@/lib/types/api"

const SEVERITY_ORDER: Record<string, number> = { blocking: 0, warning: 1, info: 2 }

export function ValidationFindings({ validation }: { validation: ValidationAgentOutput }) {
  const findings = [...validation.findings].sort(
    (a, b) => (SEVERITY_ORDER[a.severity] ?? 3) - (SEVERITY_ORDER[b.severity] ?? 3)
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Validation findings</span>
          <span className="text-xs font-normal text-muted-foreground">
            {toTitleCase(validation.verdict)} · {formatPercent(validation.confidence)} confidence
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {validation.summary && (
          <p className="text-sm text-muted-foreground">{validation.summary}</p>
        )}

        {findings.length > 0 && (
          <div className="flex flex-col divide-y">
            {findings.map((finding, i) => (
              <div key={i} className="flex flex-col gap-1.5 py-3 first:pt-0 last:pb-0">
                <div className="flex items-center gap-2">
                  <SeverityBadge severity={finding.severity} />
                  <span className="text-sm font-medium">{finding.description}</span>
                </div>
                {finding.detail && (
                  <p className="text-sm text-muted-foreground">{finding.detail}</p>
                )}
                {Object.keys(finding.evidence).length > 0 && (
                  <dl className="mt-1 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-xs">
                    {Object.entries(finding.evidence).map(([key, value]) => (
                      <div key={key} className="contents">
                        <dt className="text-muted-foreground">{toTitleCase(key)}</dt>
                        <dd className="font-mono">{value}</dd>
                      </div>
                    ))}
                  </dl>
                )}
              </div>
            ))}
          </div>
        )}

        {validation.checks.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {validation.checks.map((check, i) => (
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

        {validation.duplicate_candidates.length > 0 && (
          <div className="flex flex-col gap-2 rounded-lg bg-warning/5 p-3">
            <div className="flex items-center gap-2 text-sm font-medium text-warning">
              <CopyIcon className="size-3.5" />
              Possible duplicate claims
            </div>
            {validation.duplicate_candidates.map((dup) => (
              <p key={dup.claim_id} className="text-xs text-muted-foreground">
                Claim #{dup.claim_id} · {formatPercent(dup.score)} match
                {dup.match_reasons.length > 0 ? ` (${dup.match_reasons.join(", ")})` : ""}
              </p>
            ))}
          </div>
        )}

        {validation.budget && (
          <div className="grid grid-cols-2 gap-3 rounded-lg bg-muted/50 p-3 text-sm">
            <div>
              <p className="text-xs text-muted-foreground">Remaining budget</p>
              <p className="font-mono tabular-nums">
                {formatMoney(validation.budget.remaining_budget, validation.budget.currency ?? "INR")}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Within budget</p>
              <p className="font-medium">{validation.budget.within_budget ? "Yes" : "No"}</p>
            </div>
          </div>
        )}

        {validation.authenticity?.is_suspicious && (
          <div className="rounded-lg bg-destructive/5 p-3 text-sm text-destructive">
            <p className="font-medium">
              Authenticity concern ({formatPercent(validation.authenticity.forged_likelihood)} likelihood)
            </p>
            {validation.authenticity.reasons.map((reason, i) => (
              <p key={i} className="text-xs">
                {reason}
              </p>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
