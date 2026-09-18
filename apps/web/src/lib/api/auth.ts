import { api } from "@/lib/api/client"
import type { AuthRequest, AuthResponse } from "@/lib/types/api"

export function login(credentials: AuthRequest): Promise<AuthResponse> {
  return api.post<AuthResponse>("/auth/login", credentials)
}
