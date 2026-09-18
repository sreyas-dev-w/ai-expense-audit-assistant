"use client"

import { use, useEffect } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { ArrowLeftIcon } from "@/components/icons"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  AiDecisionBadge,
  AiRunStatusBadge,
  ClaimStatusBadge,
} from "@/components/claims/status-badge"
import { ClaimSummary } from "@/components/claims/claim-summary"
import { AuditPanel } from "@/components/audit/audit-panel"
import { DecisionForm } from "@/components/audit/decision-form"
import { useManagerClaims } from "@/hooks/use-claims"
import { useEmployeeNameMap } from "@/hooks/use-employee"
import { useSession } from "@/hooks/use-session"

export default function ApprovalDetailPage(props: PageProps<"/approvals/[claimId]">) {
  const { claimId } = use(props.params)
  const router = useRouter()
  const employee = useSession((state) => state.employee)
  const { data, isLoading } = useManagerClaims(employee?.employee_id ?? null)
  const employeeNames = useEmployeeNameMap()

  useEffect(() => {
    if (employee && !employee.is_manager) {
      router.replace("/claims")
    }
  }, [employee, router])

  const claim = data?.find((c) => c.claim_id === Number(claimId))

  if (isLoading) {
    return (
      <div className="flex flex-col gap-3">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (!claim) {
    return (
      <div className="flex flex-col items-center gap-3 py-16 text-center">
        <p className="font-medium">Claim not found</p>
        <p className="max-w-sm text-sm text-muted-foreground">
          This claim does not exist, or was not submitted by one of your reports.
        </p>
        <Button asChild variant="outline" size="sm">
          <Link href="/approvals">Back to approvals</Link>
        </Button>
      </div>
    )
  }

  const submitter = employeeNames.get(claim.employee_id)

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <Link
          href="/approvals"
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeftIcon className="size-3.5" /> Approvals
        </Link>
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="font-heading text-xl font-semibold">Claim #{claim.claim_id}</h1>
          <ClaimStatusBadge status={claim.status} />
          <AiRunStatusBadge status={claim.ai_run_status} />
          <AiDecisionBadge decision={claim.ai_decision} />
        </div>
        <p className="text-sm text-muted-foreground">
          Submitted by {submitter?.employee_name ?? claim.employee_id}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <div className="flex flex-col gap-6">
          <ClaimSummary claim={claim} />
          <DecisionForm claim={claim} />
        </div>
        <AuditPanel claim={claim} />
      </div>
    </div>
  )
}
