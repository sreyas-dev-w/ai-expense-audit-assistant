import { api } from "@/lib/api/client"
import type { EmployeeDetailsResponse, EmployeeResponse } from "@/lib/types/api"

export function getAllEmployees(signal?: AbortSignal): Promise<EmployeeResponse[]> {
  return api.get<EmployeeResponse[]>("/employees", signal)
}

export function getEmployeeDetails(
  employeeId: string,
  signal?: AbortSignal
): Promise<EmployeeDetailsResponse> {
  return api.get<EmployeeDetailsResponse>(`/employees/${employeeId}/details`, signal)
}
