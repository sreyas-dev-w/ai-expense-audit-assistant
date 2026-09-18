"use client"

import * as React from "react"
import Link from "next/link"
import { FileQuestionIcon, SearchIcon } from "lucide-react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import {
  AiDecisionBadge,
  AiRunStatusBadge,
  ClaimStatusBadge,
} from "@/components/claims/status-badge"
import { formatDate, formatMoney, toTitleCase } from "@/lib/format"
import type { ClaimDetailsResponse, EmployeeResponse } from "@/lib/types/api"

interface ClaimsTableProps {
  claims: ClaimDetailsResponse[]
  isLoading: boolean
  detailBasePath: "/claims" | "/approvals"
  employeeNames?: Map<string, EmployeeResponse>
  emptyTitle: string
  emptyDescription: string
}

export function ClaimsTable({
  claims,
  isLoading,
  detailBasePath,
  employeeNames,
  emptyTitle,
  emptyDescription,
}: ClaimsTableProps) {
  const [search, setSearch] = React.useState("")
  const [statusFilter, setStatusFilter] = React.useState<string>("all")

  const filtered = claims.filter((claim) => {
    if (statusFilter !== "all" && claim.status !== statusFilter) return false
    if (!search) return true
    const haystack = [
      claim.business_purpose,
      claim.merchant_name,
      claim.category,
      String(claim.claim_id),
      employeeNames?.get(claim.employee_id)?.employee_name,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase()
    return haystack.includes(search.toLowerCase())
  })

  const statuses = Array.from(new Set(claims.map((c) => c.status)))

  if (isLoading) {
    return (
      <div className="flex flex-col gap-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    )
  }

  if (claims.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed py-16 text-center">
        <FileQuestionIcon className="size-8 text-muted-foreground" />
        <p className="font-medium">{emptyTitle}</p>
        <p className="max-w-sm text-sm text-muted-foreground">{emptyDescription}</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-full max-w-xs">
          <SearchIcon className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search claims"
            className="pl-8"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex flex-wrap gap-1">
          <FilterChip label="All" active={statusFilter === "all"} onClick={() => setStatusFilter("all")} />
          {statuses.map((status) => (
            <FilterChip
              key={status}
              label={toTitleCase(status)}
              active={statusFilter === status}
              onClick={() => setStatusFilter(status)}
            />
          ))}
        </div>
      </div>

      <div className="rounded-xl ring-1 ring-foreground/10">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Claim</TableHead>
              {employeeNames && <TableHead>Employee</TableHead>}
              <TableHead>Category</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              <TableHead>Submitted</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>AI audit</TableHead>
              <TableHead>Recommendation</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((claim) => (
              <TableRow key={claim.claim_id} className="cursor-pointer">
                <TableCell className="p-0">
                  <Link
                    href={`${detailBasePath}/${claim.claim_id}`}
                    className="flex flex-col gap-0.5 px-4 py-3"
                  >
                    <span className="font-medium">#{claim.claim_id}</span>
                    <span className="max-w-48 truncate text-xs text-muted-foreground">
                      {claim.business_purpose ?? claim.merchant_name ?? "No description"}
                    </span>
                  </Link>
                </TableCell>
                {employeeNames && (
                  <TableCell>
                    {employeeNames.get(claim.employee_id)?.employee_name ?? claim.employee_id}
                  </TableCell>
                )}
                <TableCell>{toTitleCase(claim.category)}</TableCell>
                <TableCell className="text-right font-mono tabular-nums">
                  {formatMoney(claim.claim_amount, claim.currency)}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {formatDate(claim.claim_created_at)}
                </TableCell>
                <TableCell>
                  <ClaimStatusBadge status={claim.status} />
                </TableCell>
                <TableCell>
                  <AiRunStatusBadge status={claim.ai_run_status} />
                </TableCell>
                <TableCell>
                  <AiDecisionBadge decision={claim.ai_decision} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {filtered.length === 0 && (
        <p className="py-8 text-center text-sm text-muted-foreground">
          No claims match this search.
        </p>
      )}
    </div>
  )
}

function FilterChip({
  label,
  active,
  onClick,
}: {
  label: string
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-3 py-1 text-xs font-medium transition-colors active:scale-95 ${
        active
          ? "bg-primary text-primary-foreground"
          : "bg-muted text-muted-foreground hover:bg-muted/70"
      }`}
    >
      {label}
    </button>
  )
}
