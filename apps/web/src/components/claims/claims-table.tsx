"use client";

import Link from "next/link";

import {
  RecommendationBadge,
  StatusBadge,
} from "@/components/claims/status-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDate, formatMoney } from "@/lib/format";
import { CATEGORY_LABELS, type ClaimListItem } from "@/lib/types";

export function ClaimsTable({
  claims,
  hrefBase,
  showEmployee = false,
  actionLabel = "View",
}: {
  claims: ClaimListItem[];
  hrefBase: string;
  showEmployee?: boolean;
  actionLabel?: string;
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-16">ID</TableHead>
          {showEmployee ? <TableHead>Employee</TableHead> : null}
          <TableHead>Category</TableHead>
          <TableHead>Purpose</TableHead>
          <TableHead className="text-right">Amount</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Audit</TableHead>
          <TableHead>Filed</TableHead>
          <TableHead className="w-20" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {claims.map((claim) => (
          <TableRow key={claim.claim_id}>
            <TableCell className="font-mono text-xs">
              #{claim.claim_id}
            </TableCell>
            {showEmployee ? (
              <TableCell>{claim.employee_name ?? claim.employee_id}</TableCell>
            ) : null}
            <TableCell>
              <Badge variant="outline">{CATEGORY_LABELS[claim.category]}</Badge>
            </TableCell>
            <TableCell className="max-w-[22rem] truncate">
              {claim.business_purpose ?? "--"}
            </TableCell>
            <TableCell className="text-right tabular-nums">
              {formatMoney(claim.claim_amount, claim.currency)}
            </TableCell>
            <TableCell>
              <StatusBadge status={claim.status} />
            </TableCell>
            <TableCell>
              {claim.audit_recommendation ? (
                <RecommendationBadge
                  recommendation={claim.audit_recommendation}
                />
              ) : (
                <span className="text-muted-foreground text-xs">
                  Not audited
                </span>
              )}
            </TableCell>
            <TableCell className="text-muted-foreground text-xs">
              {formatDate(claim.claim_created_at)}
            </TableCell>
            <TableCell>
              <Button asChild variant="ghost" size="sm">
                <Link href={`${hrefBase}/${claim.claim_id}`}>{actionLabel}</Link>
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
