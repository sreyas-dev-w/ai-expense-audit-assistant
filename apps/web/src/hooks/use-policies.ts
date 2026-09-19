"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  deletePolicyDocument,
  listPolicyDocuments,
  uploadPolicyDocument,
} from "@/lib/api/policies"

export function usePolicyDocuments() {
  return useQuery({
    queryKey: ["policy-documents"],
    queryFn: ({ signal }) => listPolicyDocuments(signal),
  })
}

export function useUploadPolicyDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => uploadPolicyDocument(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["policy-documents"] })
    },
  })
}

export function useDeletePolicyDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (policyId: number) => deletePolicyDocument(policyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["policy-documents"] })
    },
  })
}