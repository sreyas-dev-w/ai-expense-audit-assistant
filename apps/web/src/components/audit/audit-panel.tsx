"use client"

import { Loader2Icon, OctagonAlertIcon } from "@/components/icons"
import { RecommendationHeader } from "@/components/audit/recommendation-header"
import { ValidationFindings } from "@/components/audit/validation-findings"
import { PolicyFindings } from "@/components/audit/policy-findings"
import { GroundingReferences } from "@/components/audit/grounding-references"
import { Skeleton } from "@/components/ui/skeleton"
import { useAgentResponse } from "@/hooks/use-agent-response"
import { splitNotes, unwrapPolicyOutput, unwrapValidationOutput } from "@/lib/format"
import type { AIDecision, ClaimDetailsResponse, ClaimPriority } from "@/lib/types/api"

export function AuditPanel({ claim }: { claim: ClaimDetailsResponse }) {
  const isProcessing = claim.ai_run_status === "pending" || claim.ai_run_status === "running"
  const { data: agentResponse, isLoading, isError } = useAgentResponse(claim.claim_id, isProcessing)

  if (claim.ai_run_status === "pending" || (claim.ai_run_status === "running" && !agentResponse)) {
    return <AuditProcessingState />
  }

  if (claim.ai_run_status === "failed") {
    return <AuditFailedState notes={claim.auditer_notes} />
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-3">
        <Skeleton className="h-28 w-full rounded-2xl" />
        <Skeleton className="h-48 w-full rounded-2xl" />
      </div>
    )
  }

  if (isError || !agentResponse) {
    return <AuditFailedState notes={null} />
  }

  const policy = unwrapPolicyOutput(agentResponse.policy_response)
  const validation = unwrapValidationOutput(agentResponse.validation_response)
  const noteLines = splitNotes(agentResponse.notes)

  return (
    <div className="flex flex-col gap-4">
      <RecommendationHeader
        decision={claim.ai_decision as AIDecision | null}
        confidence={agentResponse.confidence_score ? Number(agentResponse.confidence_score) : null}
        priority={claim.priority as ClaimPriority}
      />

      {noteLines.length > 0 && (
        <div className="rounded-xl bg-muted/50 p-4 text-sm">
          {noteLines.map((line, i) => (
            <p key={i} className={i === 0 ? "font-medium" : "text-muted-foreground"}>
              {line}
            </p>
          ))}
        </div>
      )}

      {validation && <ValidationFindings validation={validation} />}
      {policy && <PolicyFindings policy={policy} />}
      {policy && <GroundingReferences references={policy.references} />}

      {!validation && !policy && (
        <p className="rounded-xl border border-dashed p-6 text-center text-sm text-muted-foreground">
          The audit completed without a detailed validation or policy result.
        </p>
      )}
    </div>
  )
}

function AuditProcessingState() {
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed p-10 text-center">
      <Loader2Icon className="size-6 animate-spin text-primary" />
      <p className="font-medium">The AI audit is running</p>
      <p className="max-w-sm text-sm text-muted-foreground">
        Validation and policy checks are running in the background. This page updates
        automatically once they finish.
      </p>
    </div>
  )
}

function AuditFailedState({ notes }: { notes: string | null }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed p-10 text-center">
      <OctagonAlertIcon className="size-6 text-destructive" />
      <p className="font-medium">The AI audit run failed</p>
      <p className="max-w-sm text-sm text-muted-foreground">
        {notes ?? "This claim needs a manual review before a decision is made."}
      </p>
    </div>
  )
}
