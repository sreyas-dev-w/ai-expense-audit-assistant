import type { ApiErrorBody } from "@/lib/types/api"

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"

/**
 * Normalised API error. `detail` mirrors the FastAPI error body, which is a
 * plain string for most errors but an array of `{loc, msg, type}` objects for
 * request validation failures (422s) — see `apps/api` error envelope notes.
 */
export class ApiError extends Error {
  readonly status: number
  readonly detail: ApiErrorBody["detail"]

  constructor(status: number, detail: ApiErrorBody["detail"]) {
    super(ApiError.formatMessage(detail))
    this.name = "ApiError"
    this.status = status
    this.detail = detail
  }

  private static formatMessage(detail: ApiErrorBody["detail"]): string {
    if (typeof detail === "string") return detail
    if (Array.isArray(detail)) {
      return detail
        .map((d) => `${d.loc.slice(1).join(".")}: ${d.msg}`)
        .join("; ")
    }
    return "Request failed"
  }
}

async function parseError(res: Response): Promise<never> {
  let detail: ApiErrorBody["detail"] = res.statusText || "Request failed"
  try {
    const body = (await res.json()) as ApiErrorBody
    if (body?.detail) detail = body.detail
  } catch {
    // response had no JSON body
  }
  throw new ApiError(res.status, detail)
}

interface RequestOptions {
  method?: string
  body?: unknown
  formData?: FormData
  signal?: AbortSignal
}

/**
 * Thin fetch wrapper. Never sends credentials: the backend's
 * `allow_origins=["*"]` + `allow_credentials=True` CORS combination is
 * rejected by browsers for credentialed requests.
 */
async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, formData, signal } = options

  const init: RequestInit = {
    method,
    signal,
    credentials: "omit",
  }

  if (formData) {
    init.body = formData
  } else if (body !== undefined) {
    init.headers = { "Content-Type": "application/json" }
    init.body = JSON.stringify(body)
  }

  const res = await fetch(`${API_BASE_URL}${path}`, init)

  if (!res.ok) {
    await parseError(res)
  }

  if (res.status === 204) {
    return undefined as T
  }

  return (await res.json()) as T
}

export const api = {
  get: <T>(path: string, signal?: AbortSignal) => request<T>(path, { signal }),
  post: <T>(path: string, body?: unknown, signal?: AbortSignal) =>
    request<T>(path, { method: "POST", body, signal }),
  patch: <T>(path: string, body?: unknown, signal?: AbortSignal) =>
    request<T>(path, { method: "PATCH", body, signal }),
  postForm: <T>(path: string, formData: FormData, signal?: AbortSignal) =>
    request<T>(path, { method: "POST", formData, signal }),
}
