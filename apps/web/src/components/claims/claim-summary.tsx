"use client";

import { useEffect, useState } from "react";
import { ExternalLinkIcon } from "lucide-react";

import { StatusBadge } from "@/components/claims/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { fetchReceiptObjectUrl } from "@/lib/api";
import { formatDate, formatMoney, titleCase } from "@/lib/format";
import { CATEGORY_LABELS, type Claim } from "@/lib/types";

function Detail({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid gap-1">
      <dt className="text-muted-foreground text-xs">{label}</dt>
      <dd className="text-sm">{value ?? "--"}</dd>
    </div>
  );
}

function ReceiptLink({ receiptUrl }: { receiptUrl: string }) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let current: string | null = null;
    fetchReceiptObjectUrl(receiptUrl)
      .then((url) => {
        current = url;
        setObjectUrl(url);
      })
      .catch((cause) =>
        setError(cause instanceof Error ? cause.message : "Unavailable"),
      );
    return () => {
      if (current) URL.revokeObjectURL(current);
    };
  }, [receiptUrl]);

  if (error) return <span className="text-muted-foreground text-sm">{error}</span>;
  if (!objectUrl) return <span className="text-muted-foreground text-sm">Loading…</span>;

  return (
    <Button asChild variant="outline" size="sm">
      <a href={objectUrl} target="_blank" rel="noreferrer">
        <ExternalLinkIcon className="size-4" />
        Open receipt
      </a>
    </Button>
  );
}

export function ClaimSummary({
  claim,
  employeeName,
}: {
  claim: Claim;
  employeeName?: string | null;
}) {
  const categoryData = Object.entries(claim.category_data ?? {});

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <CardTitle>Claim #{claim.claim_id}</CardTitle>
          <StatusBadge status={claim.status} />
          <Badge variant="outline">{CATEGORY_LABELS[claim.category]}</Badge>
        </div>
        <CardDescription>
          {claim.business_purpose ?? "No business purpose recorded"}
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-6">
        <dl className="grid gap-4 sm:grid-cols-3">
          <Detail
            label="Amount"
            value={
              <span className="font-medium tabular-nums">
                {formatMoney(claim.claim_amount, claim.currency)}
              </span>
            }
          />
          <Detail
            label="Employee"
            value={employeeName ?? claim.employee_id}
          />
          <Detail label="Project" value={claim.project_code ?? "--"} />
          <Detail label="Merchant" value={claim.merchant_name ?? "--"} />
          <Detail label="Filed" value={formatDate(claim.claim_created_at)} />
          <Detail label="Updated" value={formatDate(claim.claim_updated_at)} />
        </dl>

        {categoryData.length > 0 ? (
          <>
            <Separator />
            <div className="grid gap-3">
              <p className="text-sm font-medium">
                {CATEGORY_LABELS[claim.category]} details
              </p>
              <dl className="grid gap-4 sm:grid-cols-3">
                {categoryData.map(([key, value]) => (
                  <Detail
                    key={key}
                    label={titleCase(key)}
                    value={
                      value === null || value === undefined || value === ""
                        ? "--"
                        : typeof value === "object"
                          ? JSON.stringify(value)
                          : String(value)
                    }
                  />
                ))}
              </dl>
            </div>
          </>
        ) : null}

        {claim.receipt_url ? (
          <>
            <Separator />
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium">Receipt</span>
              <ReceiptLink receiptUrl={claim.receipt_url} />
            </div>
          </>
        ) : null}

        {claim.auditer_notes ? (
          <>
            <Separator />
            <div className="grid gap-1">
              <p className="text-sm font-medium">
                Approver notes{claim.auditer_id ? ` (${claim.auditer_id})` : ""}
              </p>
              <p className="text-muted-foreground text-sm whitespace-pre-wrap">
                {claim.auditer_notes}
              </p>
            </div>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}
