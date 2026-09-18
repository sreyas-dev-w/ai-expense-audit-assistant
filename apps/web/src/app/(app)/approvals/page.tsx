"use client"

import { ClaimsTable } from "@/components/claims/claims-table"
import { useManagerClaims } from "@/hooks/use-claims"
import { useEmployeeNameMap } from "@/hooks/use-employee"
import { useSession } from "@/hooks/use-session"

export default function ApprovalsPage() {
  const managerId = useSession((state) => state.employee?.employee_id ?? null)
  const { data, isLoading } = useManagerClaims(managerId)
  const employeeNames = useEmployeeNameMap()

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="font-heading text-xl font-semibold">Approvals</h1>
        <p className="text-sm text-muted-foreground">
          Claims submitted by your direct reports, with the AI recommendation for each.
        </p>
      </div>

      <ClaimsTable
        claims={data ?? []}
        isLoading={isLoading}
        detailBasePath="/approvals"
        employeeNames={employeeNames}
        emptyTitle="Nothing to review"
        emptyDescription="Claims submitted by your team will show up here once they are audited."
      />
    </div>
  )
}
