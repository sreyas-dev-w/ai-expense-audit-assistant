"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { getEmployeeClaims, getManagerClaims, submitClaim, updateClaimAudit } from "@/lib/api/claims"
import type { ClaimAuditUpdate, ClaimCreate } from "@/lib/types/api"

export function useEmployeeClaims(employeeId: string | null) {
  return useQuery({
    queryKey: ["employee-claims", employeeId],
    queryFn: ({ signal }) => getEmployeeClaims(employeeId as string, signal),
    enabled: !!employeeId,
    // AI audit runs in a background task with no websocket/SSE; poll while
    // any claim in the list is still being processed.
    refetchInterval: (query) => {
      const claims = query.state.data
      if (!claims) return false
      const isProcessing = claims.some(
        (claim) => claim.ai_run_status === "pending" || claim.ai_run_status === "running"
      )
      return isProcessing ? 3000 : false
    },
  })
}

export function useManagerClaims(managerId: string | null) {
  return useQuery({
    queryKey: ["manager-claims", managerId],
    queryFn: ({ signal }) => getManagerClaims(managerId as string, signal),
    enabled: !!managerId,
    refetchInterval: (query) => {
      const claims = query.state.data
      if (!claims) return false
      const isProcessing = claims.some(
        (claim) => claim.ai_run_status === "pending" || claim.ai_run_status === "running"
      )
      return isProcessing ? 3000 : false
    },
  })
}

export function useSubmitClaim() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ claim, receipt }: { claim: ClaimCreate; receipt: File }) =>
      submitClaim(claim, receipt),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employee-claims"] })
    },
  })
}

export function useUpdateClaimAudit() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ claimId, data }: { claimId: number; data: ClaimAuditUpdate }) =>
      updateClaimAudit(claimId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["manager-claims"] })
      queryClient.invalidateQueries({ queryKey: ["employee-claims"] })
    },
  })
}
