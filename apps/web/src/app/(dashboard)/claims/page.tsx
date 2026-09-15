"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus, ReceiptText, SearchX } from "lucide-react";
import Link from "next/link";
import { api, formatCurrency, formatDate } from "@/lib/api";
import { useUser } from "@/hooks/use-user";
import type { ClaimStatus } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "cn";

const STATUS_FILTERS: Array<{ label: string; value: ClaimStatus | "All" }> = [
  { label: "All", value: "All" },
  { label: "Draft", value: "Draft" },
  { label: "Under Review", value: "Under Review" },
  { label: "Approved", value: "Approved" },
  { label: "Failed", value: "Failed" },
];

export default function MyClaimsPage() {
  const { user } = useUser();
  const [filter, setFilter] = React.useState<ClaimStatus | "All">("All");

  const userId = user?.employee_id;

  const { data: claims = [], isLoading, error } = useQuery({
    queryKey: ["claims", userId, filter],
    queryFn: () => api.getMyClaims(userId!, filter === "All" ? undefined : filter),
    enabled: !!userId,
  });

  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-8">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">My Claims</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {user ? (
              <>
                Showing historical claims for <span className="text-foreground">{user.employee_name}</span>
                {" "}({user.employee_id}).
              </>
            ) : (
              "Loading your profile…"
            )}
          </p>
        </div>
        <Button asChild className="gap-1.5">
          <Link href="/claims/new">
            <Plus className="size-4" /> New claim
          </Link>
        </Button>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-1.5 border-b border-border pb-px">
        {STATUS_FILTERS.map((option) => {
          const active = filter === option.value;
          return (
            <button
              key={option.value}
              onClick={() => setFilter(option.value)}
              className={cn(
                "rounded-t-lg border-b-2 px-3 py-2 text-sm transition-colors",
                active
                  ? "border-primary text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              {option.label}
            </button>
          );
        })}
      </div>

      {isLoading && <ClaimsTableSkeleton />}

      {!isLoading && error && (
        <EmptyState
          icon={<SearchX className="size-6" />}
          title="Unable to load claims"
          description={(error as Error).message}
        />
      )}

      {!isLoading && !error && claims.length === 0 && (
        <EmptyState
          icon={<ReceiptText className="size-6" />}
          title="No claims here yet"
          description={
            filter === "All"
              ? "Submit your first claim to kick off the AI audit pipeline."
              : `No claims currently match the “${filter}” filter.`
          }
          action={
            <Button asChild size="sm" className="gap-1.5">
              <Link href="/claims/new">
                <Plus className="size-4" /> Create a claim
              </Link>
            </Button>
          }
        />
      )}

      {!isLoading && !error && claims.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead>Claim</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Submitted</TableHead>
                <TableHead className="text-right">Review</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {claims.map((claim) => (
                <TableRow key={claim.claim_id}>
                  <TableCell>
                    <div className="min-w-0">
                      <p className="truncate font-medium text-foreground">
                        {claim.claim_name}
                      </p>
                      <p className="text-xs text-muted-foreground">#{claim.claim_id}</p>
                    </div>
                  </TableCell>
                  <TableCell className="font-medium tabular-nums text-foreground">
                    {formatCurrency(claim.estimated_amount)}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={claim.status} />
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDate(claim.created_at)}
                  </TableCell>
                  <TableCell className="text-right text-xs text-muted-foreground">
                    {claim.requires_human_review ? "Human review" : "Auto"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

function ClaimsTableSkeleton() {
  return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: 5 }).map((_, index) => (
        <Skeleton key={index} className="h-12 w-full rounded-lg" />
      ))}
    </div>
  );
}

function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border px-6 py-16 text-center">
      <div className="flex size-12 items-center justify-center rounded-xl bg-muted text-muted-foreground">
        {icon}
      </div>
      <p className="mt-2 font-medium text-foreground">{title}</p>
      <p className="max-w-sm text-sm text-muted-foreground">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}