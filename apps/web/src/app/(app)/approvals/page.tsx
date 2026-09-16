"use client";

import { useQuery } from "@tanstack/react-query";

import { ClaimsTable } from "@/components/claims/claims-table";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import type { ClaimListItem } from "@/lib/types";

const DECIDED = new Set(["approved", "rejected"]);

function split(claims: ClaimListItem[]) {
  return {
    pending: claims.filter((claim) => !DECIDED.has(claim.status)),
    decided: claims.filter((claim) => DECIDED.has(claim.status)),
  };
}

export default function ApprovalsPage() {
  const { data, isPending, error } = useQuery({
    queryKey: ["claims", "team"],
    queryFn: () => api.listClaims("team"),
    refetchInterval: 15_000,
  });

  const { pending, decided } = split(data ?? []);

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-xl font-semibold">Approve claims</h1>
        <p className="text-muted-foreground text-sm">
          Claims filed by your direct reports, with the assistant&apos;s
          recommendation.
        </p>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Could not load team claims</AlertTitle>
          <AlertDescription>{error.message}</AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Awaiting your decision</CardTitle>
          <CardDescription>
            {isPending
              ? "Loading"
              : `${pending.length} claim${pending.length === 1 ? "" : "s"}`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isPending ? (
            <div className="grid gap-2">
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-9 w-full" />
            </div>
          ) : pending.length > 0 ? (
            <ClaimsTable
              claims={pending}
              hrefBase="/approvals"
              showEmployee
              actionLabel="Review"
            />
          ) : (
            <p className="text-muted-foreground py-8 text-center text-sm">
              Nothing waiting on you right now.
            </p>
          )}
        </CardContent>
      </Card>

      {decided.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Already decided</CardTitle>
            <CardDescription>
              {decided.length} claim{decided.length === 1 ? "" : "s"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ClaimsTable
              claims={decided}
              hrefBase="/approvals"
              showEmployee
              actionLabel="View"
            />
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
