import { api } from "@/lib/api/client"
import type { PolicyDocumentSummary, PolicyIngestResult } from "@/lib/types/api"

export function uploadPolicyDocument(
  file: File,
  force = false
): Promise<PolicyIngestResult> {
  const formData = new FormData()
  formData.append("file", file)
  formData.append("force", String(force))
  return api.postForm<PolicyIngestResult>("/api/v1/policies/documents", formData)
}

export function listPolicyDocuments(
  signal?: AbortSignal
): Promise<PolicyDocumentSummary[]> {
  return api.get<PolicyDocumentSummary[]>("/api/v1/policies/documents", signal)
}

export function deletePolicyDocument(
  policyId: number,
  signal?: AbortSignal
): Promise<void> {
  return api.delete<void>(`/api/v1/policies/documents/${policyId}`, signal)
}