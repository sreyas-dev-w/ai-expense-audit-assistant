"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeftIcon } from "lucide-react";

import { AuditPanel } from "@/components/audit/audit-panel";
import { ClaimSummary } from "@/components/claims/claim-summary";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, api } from "@/lib/api";

export default function ClaimDetailPage() {
  const params = useParams<{ claimId: string }>();
  const claimId = Number(params.claimId);

  const claimQuery = useQuery({
    queryKey: ["claims", claimId],
    queryFn: () => api.getClaim(claimId),
    enabled: Number.isFinite(claimId),
  });

  const auditQuery = useQuery({
    queryKey: ["audit", claimId],
    queryFn: () => api.getAudit(claimId),
    enabled: Number.isFinite(claimId),
    // 404 simply means the audit has not run; there is nothing to retry.
    retry: (count, error) =>
      !(error instanceof ApiError && error.status === 404) && count < 1,
  });

  const auditMissing =
    auditQuery.error instanceof ApiError && auditQuery.error.status === 404;

  return (
    <div className="mx-auto grid w-full max-w-4xl gap-6">
      <div>
        <Button asChild variant="ghost" size="sm">
          <Link href="/claims">
            <ArrowLeftIcon className="size-4" />
            Back to claims
          </Link>
        </Button>
      </div>

      {claimQuery.isPending ? (
        <Skeleton className="h-64 w-full" />
      ) : claimQuery.error ? (
        <Alert variant="destructive">
          <AlertTitle>Could not load this claim</AlertTitle>
          <AlertDescription>{claimQuery.error.message}</AlertDescription>
        </Alert>
      ) : (
        <ClaimSummary claim={claimQuery.data} />
      )}

      {auditQuery.isPending ? (
        <Skeleton className="h-48 w-full" />
      ) : auditMissing ? (
        <Alert>
          <AlertTitle>No audit yet</AlertTitle>
          <AlertDescription>
            The audit workflow has not produced a result for this claim.
          </AlertDescription>
        </Alert>
      ) : auditQuery.data ? (
        <AuditPanel audit={auditQuery.data} />
      ) : null}
    </div>
  );
}
