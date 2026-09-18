"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { useSession } from "@/hooks/use-session"
import { Skeleton } from "@/components/ui/skeleton"

/**
 * Waits for the persisted session to rehydrate from sessionStorage before
 * deciding whether to redirect. Without this, a page refresh would briefly
 * read `employee: null` and bounce an already-logged-in user to /login.
 */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const hasHydrated = useSession((state) => state.hasHydrated)
  const employee = useSession((state) => state.employee)

  React.useEffect(() => {
    if (hasHydrated && !employee) {
      router.replace("/login")
    }
  }, [hasHydrated, employee, router])

  if (!hasHydrated || !employee) {
    return (
      <div className="flex min-h-[100dvh] items-center justify-center p-8">
        <div className="w-full max-w-sm space-y-3">
          <Skeleton className="h-8 w-2/3" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
        </div>
      </div>
    )
  }

  return <>{children}</>
}
