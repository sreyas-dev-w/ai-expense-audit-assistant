"use client";

import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  ChevronDown,
  Inbox,
  Loader2,
  ShieldAlert,
  XCircle,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { api, formatCurrency, formatDate } from "@/lib/api";
import { useUser } from "@/hooks/use-user";
import type { TeamClaimResponse } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "cn";

export default function TeamApprovalsPage() {
  const { user, isManager, isLoading: userLoading } = useUser();
  const queryClient = useQueryClient();
  const router = useRouter();
  const [expanded, setExpanded] = React.useState<Set<number>>(new Set());

  const managerId = user?.employee_id;

  const { data: approvals = [], isLoading: claimsLoading } = useQuery({
    queryKey: ["approvals", managerId],
    queryFn: () => api.getTeamApprovals(managerId!),
    enabled: !!managerId && isManager,
  });

  const decision = useMutation({
    mutationFn: ({
      claim,
      action,
    }: {
      claim: TeamClaimResponse;
      action: "approve" | "reject";
    }) =>
      action === "approve"
        ? api.approveClaim(claim.claim_id, managerId!)
        : api.rejectClaim(claim.claim_id, managerId!, "Manager rejected this claim"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
      queryClient.invalidateQueries({ queryKey: ["claims"] });
    },
  });

  const isLoading = userLoading || claimsLoading;

  const toggleRow = (claimId: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(claimId)) {
        next.delete(claimId);
      } else {
        next.add(claimId);
      }
      return next;
    });
  };

  if (!isLoading && !isManager) {
    return (
      <div className="mx-auto w-full max-w-6xl px-6 py-8">
        <ManagerGuard
          title="Team Approvals requires a manager"
          description="The logged-in profile has no direct reports. Switch to a manager profile from the sidebar switcher to see the approval inbox."
          onSwitch={() => router.push("/claims")}
        />
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-foreground">Team Approvals</h1>
        <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          Claims marked <StatusBadge status="Under Review" /> submitted by{" "}
          <span className="text-foreground">your direct reports</span>.
          {managerId && (
            <Badge variant="outline" className="gap-1">
              <ShieldAlert className="size-3" /> {managerId}
            </Badge>
          )}
        </p>
      </div>

      {isLoading && <ApprovalsSkeleton />}

      {!isLoading && approvals.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border px-6 py-16 text-center">
          <div className="flex size-12 items-center justify-center rounded-xl bg-muted text-muted-foreground">
            <Inbox className="size-6" />
          </div>
          <p className="mt-2 font-medium text-foreground">Approval inbox is empty</p>
          <p className="max-w-sm text-sm text-muted-foreground">
            Claims submitted by your direct reports will appear here once they pass the AI audit
            pipeline and move to “Under Review”.
          </p>
        </div>
      )}

      {!isLoading && approvals.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead className="w-8" />
                <TableHead>Claim</TableHead>
                <TableHead>Employee</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Submitted</TableHead>
                <TableHead className="text-right">Decision</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {approvals.map((claim) => {
                const isOpen = expanded.has(claim.claim_id);
                const isPending =
                  decision.isPending &&
                  decision.variables?.claim.claim_id === claim.claim_id;
                return (
                  <React.Fragment key={claim.claim_id}>
                    <TableRow className="cursor-pointer" onClick={() => toggleRow(claim.claim_id)}>
                      <TableCell>
                        <ChevronDown
                          className={cn(
                            "size-4 text-muted-foreground transition-transform",
                            isOpen && "rotate-180"
                          )}
                        />
                      </TableCell>
                      <TableCell>
                        <p className="font-medium text-foreground">{claim.claim_name}</p>
                        <p className="text-xs text-muted-foreground">#{claim.claim_id}</p>
                      </TableCell>
                      <TableCell>
                        <p className="font-medium text-foreground">{claim.employee_name}</p>
                        <p className="text-xs text-muted-foreground">
                          {claim.employee_id} · {claim.job_level}
                        </p>
                      </TableCell>
                      <TableCell className="font-medium tabular-nums text-foreground">
                        {formatCurrency(claim.estimated_amount)}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDate(claim.created_at)}
                      </TableCell>
                      <TableCell>
                        <div
                          className="flex items-center justify-end gap-2"
                          onClick={(event) => event.stopPropagation()}
                        >
                          <Button
                            size="sm"
                            variant="ghost"
                            className="gap-1 text-success hover:bg-success/10 hover:text-success"
                            disabled={isPending}
                            onClick={() => decision.mutate({ claim, action: "approve" })}
                          >
                            {isPending ? <Loader2 className="size-3.5 animate-spin" /> : <CheckCircle2 className="size-3.5" />}
                            Approve
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="gap-1 text-destructive hover:bg-destructive/10 hover:text-destructive"
                            disabled={isPending}
                            onClick={() => decision.mutate({ claim, action: "reject" })}
                          >
                            <XCircle className="size-3.5" />
                            Reject
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                    {isOpen && (
                      <TableRow className="border-0 hover:bg-transparent">
                        <TableCell />
                        <TableCell colSpan={5} className="bg-input/10 pb-4">
                          <div className="flex flex-col gap-3 rounded-lg border border-border bg-card p-3">
                            <div className="flex items-center gap-2 text-xs">
                              <StatusBadge status="Under Review" />
                              <span className="text-muted-foreground">
                                Requires human review · OCR metadata extracted by{" "}
                                <span className="font-medium text-foreground">ocr_agent</span>
                              </span>
                            </div>
                            <div className="grid gap-2 text-xs sm:grid-cols-3">
                              <OcrField label="Merchant" value={claim.ocr_text?.merchant} />
                              <OcrField label="Date" value={claim.ocr_text?.date} />
                              <OcrField
                                label="Total amount"
                                value={
                                  claim.ocr_text ? formatCurrency(claim.ocr_text.total_amount) : undefined
                                }
                              />
                            </div>
                            {claim.violations && (
                              <div className="rounded-lg border border-caution/30 bg-caution/10 p-3 text-xs text-caution">
                                {claim.violations}
                              </div>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </React.Fragment>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

function OcrField({ label, value }: { label: string; value?: string }) {
  return (
    <div className="rounded-lg border border-border bg-input/20 px-2.5 py-2">
      <p className="text-muted-foreground">{label}</p>
      <p className="mt-0.5 font-medium text-foreground">{value ?? "—"}</p>
    </div>
  );
}

function ApprovalsSkeleton() {
  return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: 4 }).map((_, index) => (
        <Skeleton key={index} className="h-14 w-full rounded-lg" />
      ))}
    </div>
  );
}

function ManagerGuard({
  title,
  description,
  onSwitch,
}: {
  title: string;
  description: string;
  onSwitch: () => void;
}) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border px-6 py-16 text-center">
      <div className="flex size-12 items-center justify-center rounded-xl bg-muted text-muted-foreground">
        <Inbox className="size-6" />
      </div>
      <p className="mt-2 font-medium text-foreground">{title}</p>
      <p className="text-sm text-muted-foreground">{description}</p>
      <Button variant="outline" size="sm" className="mt-4" onClick={onSwitch}>
        Go to My Claims
      </Button>
    </div>
  );
}