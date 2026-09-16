"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeftIcon, Loader2Icon, PlayIcon } from "lucide-react";
import { toast } from "sonner";

import { AuditPanel } from "@/components/audit/audit-panel";
import { useAuth } from "@/components/auth-provider";
import { ClaimSummary } from "@/components/claims/claim-summary";
import { DecisionDialog } from "@/components/claims/decision-dialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, api } from "@/lib/api";

export default function ApprovalReviewPage() {
  const params = useParams<{ claimId: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { profile, loading } = useAuth();
  const claimId = Number(params.claimId);

  // The sidebar already hides this route for non-managers, and the API
  // enforces it again; this is only so a pasted URL does not sit on a spinner.
  useEffect(() => {
    if (!loading && profile && !profile.is_manager) router.replace("/claims");
  }, [loading, profile, router]);

  const claimQuery = useQuery({
    queryKey: ["claims", claimId],
    queryFn: () => api.getClaim(claimId),
    enabled: Number.isFinite(claimId),
  });

  const auditQuery = useQuery({
    queryKey: ["audit", claimId],
    queryFn: () => api.getAudit(claimId),
    enabled: Number.isFinite(claimId),
    retry: (count, error) =>
      !(error instanceof ApiError && error.status === 404) && count < 1,
  });

  const rerun = useMutation({
    mutationFn: () => api.runAudit(claimId),
    onSuccess: async () => {
      toast.success("Audit finished");
      await queryClient.invalidateQueries({ queryKey: ["audit", claimId] });
      await queryClient.invalidateQueries({ queryKey: ["claims"] });
    },
    onError: (error) =>
      toast.error("The audit run failed", {
        description: error instanceof Error ? error.message : undefined,
      }),
  });

  const auditMissing =
    auditQuery.error instanceof ApiError && auditQuery.error.status === 404;
  const claim = claimQuery.data;
  const decided = claim?.status === "approved" || claim?.status === "rejected";

  return (
    <div className="mx-auto grid w-full max-w-4xl gap-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Button asChild variant="ghost" size="sm">
          <Link href="/approvals">
            <ArrowLeftIcon className="size-4" />
            Back to approvals
          </Link>
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={rerun.isPending}
          onClick={() => rerun.mutate()}
        >
          {rerun.isPending ? (
            <Loader2Icon className="size-4 animate-spin" />
          ) : (
            <PlayIcon className="size-4" />
          )}
          {auditMissing ? "Run audit" : "Re-run audit"}
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
            Run the audit to see validation findings and policy references
            before deciding.
          </AlertDescription>
        </Alert>
      ) : auditQuery.data ? (
        <AuditPanel audit={auditQuery.data} />
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Your decision</CardTitle>
          <CardDescription>
            {decided
              ? "This claim has already been decided."
              : "Approve or reject the claim. A note is required either way."}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          <DecisionDialog
            claimId={claimId}
            decision="approve"
            disabled={decided || claimQuery.isPending}
          />
          <DecisionDialog
            claimId={claimId}
            decision="reject"
            disabled={decided || claimQuery.isPending}
          />
        </CardContent>
      </Card>
    </div>
  );
}
