"use client"

import { use } from "react"
import Link from "next/link"
import { ArrowLeftIcon } from "@/components/icons"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  AiDecisionBadge,
  AiRunStatusBadge,
  ClaimStatusBadge,
} from "@/components/claims/status-badge"
import { ClaimSummary } from "@/components/claims/claim-summary"
import { useEmployeeClaims } from "@/hooks/use-claims"
import { useSession } from "@/hooks/use-session"

export default function ClaimDetailPage(props: PageProps<"/claims/[claimId]">) {
  const { claimId } = use(props.params)
  const employeeId = useSession((state) => state.employee?.employee_id ?? null)
  const { data, isLoading } = useEmployeeClaims(employeeId)

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
          This claim does not exist, or does not belong to your account.
        </p>
        <Button asChild variant="outline" size="sm">
          <Link href="/claims">Back to my claims</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <Link
          href="/claims"
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeftIcon className="size-3.5" /> My claims
        </Link>
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="font-heading text-xl font-semibold">Claim #{claim.claim_id}</h1>
          <ClaimStatusBadge status={claim.status} />
          <AiRunStatusBadge status={claim.ai_run_status} />
          <AiDecisionBadge decision={claim.ai_decision} />
        </div>
      </div>

      <ClaimSummary claim={claim} />
    </div>
  )
}
