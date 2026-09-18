"use client"

import { useQuery } from "@tanstack/react-query"
import { getAgentResponse } from "@/lib/api/claims"

/**
 * The `agent_response` row is created eagerly (and empty) at claim
 * submission, then filled in once the audit graph finishes. Poll while the
 * corresponding claim is still `pending`/`running`.
 */
export function useAgentResponse(claimId: number | null, isProcessing: boolean) {
  return useQuery({
    queryKey: ["agent-response", claimId],
    queryFn: ({ signal }) => getAgentResponse(claimId as number, signal),
    enabled: !!claimId,
    retry: false,
    refetchInterval: isProcessing ? 3000 : false,
  })
}
