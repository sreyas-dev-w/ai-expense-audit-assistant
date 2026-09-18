import { api } from "@/lib/api/client"
import type { AuditResult } from "@/lib/types/api"

export function runAudit(claimId: number): Promise<AuditResult> {
  return api.post<AuditResult>(`/api/v1/audits/${claimId}/run`)
}
