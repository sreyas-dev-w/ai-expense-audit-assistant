"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { FilePlus2Icon } from "lucide-react";

import { ClaimsTable } from "@/components/claims/claims-table";
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
import { api } from "@/lib/api";

export default function ClaimsPage() {
  const { data, isPending, error } = useQuery({
    queryKey: ["claims", "mine"],
    queryFn: () => api.listClaims("mine"),
    // Audits finish in the background, so keep the status column fresh.
    refetchInterval: 15_000,
  });

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">My claims</h1>
          <p className="text-muted-foreground text-sm">
            Every expense claim you have filed, with its audit outcome.
          </p>
        </div>
        <Button asChild>
          <Link href="/claims/new">
            <FilePlus2Icon className="size-4" />
            New claim
          </Link>
        </Button>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertTitle>Could not load claims</AlertTitle>
          <AlertDescription>{error.message}</AlertDescription>
        </Alert>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>Claims</CardTitle>
          <CardDescription>
            {data ? `${data.length} claim${data.length === 1 ? "" : "s"}` : "Loading"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isPending ? (
            <div className="grid gap-2">
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-9 w-full" />
            </div>
          ) : data && data.length > 0 ? (
            <ClaimsTable claims={data} hrefBase="/claims" />
          ) : (
            <p className="text-muted-foreground py-8 text-center text-sm">
              No claims yet. Use “New claim” to file your first one.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
