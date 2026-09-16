/** Thin fetch wrapper around the FastAPI backend. */
import type {
  AuditRunResponse,
  Claim,
  ClaimDecision,
  ClaimListItem,
  EmployeeProfile,
  LoginResponse,
} from "@/lib/types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const TOKEN_STORAGE_KEY = "expense-audit.token";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function readToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

/** FastAPI's `detail` is a string for our handlers and an array for 422s. */
function describe(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) =>
        typeof item === "object" && item !== null && "msg" in item
          ? String((item as { msg: unknown }).msg)
          : null,
      )
      .filter(Boolean);
    if (messages.length) return messages.join("; ");
  }
  return fallback;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = readToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers });

  if (!response.ok) {
    let detail: unknown = null;
    try {
      detail = (await response.json())?.detail ?? null;
    } catch {
      // Non-JSON error body; fall back to the status text.
    }
    throw new ApiError(
      response.status,
      describe(detail, response.statusText || "Request failed"),
    );
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  login(email: string, password: string) {
    return request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },

  me() {
    return request<EmployeeProfile>("/auth/me");
  },

  listClaims(scope: "mine" | "team") {
    return request<ClaimListItem[]>(`/claims?scope=${scope}`);
  },

  getClaim(claimId: number) {
    return request<Claim>(`/claims/${claimId}`);
  },

  createClaim(payload: unknown, receipt: File | null) {
    const body = new FormData();
    body.append("payload", JSON.stringify(payload));
    if (receipt) body.append("receipt", receipt);
    return request<Claim>("/claims", { method: "POST", body });
  },

  decideClaim(claimId: number, decision: ClaimDecision, notes: string) {
    return request<Claim>(`/claims/${claimId}/decision`, {
      method: "POST",
      body: JSON.stringify({ decision, notes }),
    });
  },

  /** Kicks off the LangGraph audit. The receipt is read from the stored claim. */
  runAudit(claimId: number) {
    const body = new FormData();
    body.append("claim_id", String(claimId));
    body.append("persist", "true");
    return request<AuditRunResponse>("/audits", { method: "POST", body });
  },

  getAudit(claimId: number) {
    return request<AuditRunResponse>(`/audits/${claimId}`);
  },
};

/** Authenticated receipt fetch; returns an object URL the caller must revoke. */
export async function fetchReceiptObjectUrl(
  receiptUrl: string,
): Promise<string> {
  const storedName = receiptUrl.split(/[\\/]/).pop();
  const token = readToken();
  const response = await fetch(`${API_BASE_URL}/uploads/receipts/${storedName}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!response.ok) {
    throw new ApiError(response.status, "Could not load the receipt");
  }
  return URL.createObjectURL(await response.blob());
}
