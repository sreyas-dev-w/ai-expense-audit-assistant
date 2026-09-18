"use client"

import { useQuery } from "@tanstack/react-query"
import { getAllEmployees } from "@/lib/api/employees"
import type { EmployeeResponse } from "@/lib/types/api"

/**
 * Claim list endpoints only return `employee_id`. There is no endpoint that
 * joins in the employee name, so approvals/claims tables resolve names
 * client-side from the full employee directory.
 */
export function useAllEmployees() {
  return useQuery({
    queryKey: ["employees"],
    queryFn: ({ signal }) => getAllEmployees(signal),
    staleTime: 5 * 60_000,
  })
}

export function useEmployeeNameMap(): Map<string, EmployeeResponse> {
  const { data } = useAllEmployees()
  const map = new Map<string, EmployeeResponse>()
  data?.forEach((employee) => map.set(employee.employee_id, employee))
  return map
}
