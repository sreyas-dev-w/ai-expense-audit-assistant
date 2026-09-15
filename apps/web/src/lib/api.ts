import type {
  ApprovalActionResponse,
  Claim,
  Employee,
  SubmitResponse,
  TeamClaimResponse,
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(init?.headers ?? {}),
    },
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore parse errors
    }
    throw new Error(detail);
  }

  return res.json() as Promise<T>;
}

export const api = {
  getEmployees: () => request<Employee[]>("/employees"),

  getEmployee: (employeeId: string) => request<Employee>(`/employees/${employeeId}`),

  getMyClaims: (employeeId: string, status?: string) => {
    const params = new URLSearchParams({ employee_id: employeeId });
    if (status) params.set("status", status);
    return request<Claim[]>(`/claims?${params.toString()}`);
  },

  getTeamApprovals: (managerId: string) =>
    request<TeamClaimResponse[]>(`/claims/team?manager_id=${encodeURIComponent(managerId)}`),

  submitClaim: (formData: FormData) =>
    request<SubmitResponse>("/claims/submit", { method: "POST", body: formData }),

  approveClaim: (claimId: number, managerId: string) =>
    request<ApprovalActionResponse>(`/claims/${claimId}/approve`, {
      method: "PATCH",
      body: JSON.stringify({ manager_id: managerId }),
    }),

  rejectClaim: (claimId: number, managerId: string, note?: string) =>
    request<ApprovalActionResponse>(`/claims/${claimId}/reject`, {
      method: "PATCH",
      body: JSON.stringify({ manager_id: managerId, note }),
    }),
};

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}