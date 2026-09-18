import { api } from "@/lib/api/client"
import type {
  AgentResponseDetails,
  ClaimAuditUpdate,
  ClaimCreate,
  ClaimDetailsResponse,
  ClaimSubmissionResponse,
} from "@/lib/types/api"

export function getEmployeeClaims(
  employeeId: string,
  signal?: AbortSignal
): Promise<ClaimDetailsResponse[]> {
  return api.get<ClaimDetailsResponse[]>(`/employees/${employeeId}/claims`, signal)
}

export function getManagerClaims(
  managerId: string,
  signal?: AbortSignal
): Promise<ClaimDetailsResponse[]> {
  return api.get<ClaimDetailsResponse[]>(
    `/api/v1/claims/managers/${managerId}/claims`,
    signal
  )
}

export function getAgentResponse(
  claimId: number,
  signal?: AbortSignal
): Promise<AgentResponseDetails> {
  return api.get<AgentResponseDetails>(`/api/v1/claims/${claimId}/agent-response`, signal)
}

export function updateClaimAudit(
  claimId: number,
  data: ClaimAuditUpdate
): Promise<ClaimDetailsResponse> {
  return api.patch<ClaimDetailsResponse>(`/api/v1/claims/${claimId}/audit`, data)
}

export function submitClaim(
  claim: ClaimCreate,
  receipt: File
): Promise<ClaimSubmissionResponse> {
  const formData = new FormData()
  formData.append("claim_json", JSON.stringify(claim))
  formData.append("receipt", receipt)
  return api.postForm<ClaimSubmissionResponse>("/api/v1/claims", formData)
}
