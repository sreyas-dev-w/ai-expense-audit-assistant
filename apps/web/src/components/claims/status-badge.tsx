import { Badge } from "@/components/ui/badge";
import { STATUS_LABELS } from "@/lib/format";
import type { AuditRecommendation, ClaimStatus } from "@/lib/types";

type Variant = React.ComponentProps<typeof Badge>["variant"];

const STATUS_VARIANT: Record<ClaimStatus, Variant> = {
  draft: "outline",
  submitted: "secondary",
  in_audit: "secondary",
  approved: "default",
  rejected: "destructive",
  needs_revision: "outline",
};

export function StatusBadge({ status }: { status: ClaimStatus }) {
  return <Badge variant={STATUS_VARIANT[status]}>{STATUS_LABELS[status]}</Badge>;
}

const RECOMMENDATION_LABELS: Record<AuditRecommendation, string> = {
  RECOMMEND_APPROVE: "Recommends approve",
  RECOMMEND_REJECT: "Recommends reject",
  FLAG_FOR_REVIEW: "Flagged for review",
};

const RECOMMENDATION_VARIANT: Record<AuditRecommendation, Variant> = {
  RECOMMEND_APPROVE: "default",
  RECOMMEND_REJECT: "destructive",
  FLAG_FOR_REVIEW: "secondary",
};

export function RecommendationBadge({
  recommendation,
}: {
  recommendation: AuditRecommendation;
}) {
  return (
    <Badge variant={RECOMMENDATION_VARIANT[recommendation]}>
      {RECOMMENDATION_LABELS[recommendation]}
    </Badge>
  );
}
