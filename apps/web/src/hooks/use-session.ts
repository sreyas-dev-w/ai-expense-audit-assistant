"use client"

import { create } from "zustand"
import { createJSONStorage, persist } from "zustand/middleware"
import type { EmployeeDetailsResponse, EmployeeResponse } from "@/lib/types/api"

interface SessionState {
  employee: EmployeeResponse | null
  details: EmployeeDetailsResponse | null
  hasHydrated: boolean
  setSession: (employee: EmployeeResponse, details: EmployeeDetailsResponse) => void
  clearSession: () => void
  setHasHydrated: (value: boolean) => void
}

/**
 * Session lives in `sessionStorage`: it survives a page refresh but is gone
 * once the tab closes, as specified. `hasHydrated` lets consumers (the auth
 * gate) wait for the persisted value to load before deciding to redirect —
 * otherwise a refresh would briefly look logged-out and bounce to /login.
 */
export const useSession = create<SessionState>()(
  persist(
    (set) => ({
      employee: null,
      details: null,
      hasHydrated: false,
      setSession: (employee, details) => set({ employee, details }),
      clearSession: () => set({ employee: null, details: null }),
      setHasHydrated: (value) => set({ hasHydrated: value }),
    }),
    {
      name: "expense-audit-session",
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({ employee: state.employee, details: state.details }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true)
      },
    }
  )
)

export function useIsManager(): boolean {
  return useSession((state) => state.employee?.is_manager ?? false)
}

export function useCurrentEmployeeId(): string | null {
  return useSession((state) => state.employee?.employee_id ?? null)
}
