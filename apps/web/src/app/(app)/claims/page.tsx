"use client"

import Link from "next/link"
import { PlusIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ClaimsTable } from "@/components/claims/claims-table"
import { useEmployeeClaims } from "@/hooks/use-claims"
import { useSession } from "@/hooks/use-session"

export default function MyClaimsPage() {
  const employeeId = useSession((state) => state.employee?.employee_id ?? null)
  const { data, isLoading } = useEmployeeClaims(employeeId)

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-xl font-semibold">My claims</h1>
          <p className="text-sm text-muted-foreground">
            Every expense claim you have submitted and its current status.
          </p>
        </div>
        <Button asChild size="sm">
          <Link href="/claims/new">
            <PlusIcon /> New claim
          </Link>
        </Button>
      </div>

      <ClaimsTable
        claims={data ?? []}
        isLoading={isLoading}
        detailBasePath="/claims"
        emptyTitle="No claims yet"
        emptyDescription="Submit your first expense claim to see it appear here with its AI audit status."
      />
    </div>
  )
}
