import { Badge } from "@/components/ui/badge";
import { cn } from "cn";
import type { ClaimStatus } from "@/lib/types";

const STATUS_STYLES: Record<ClaimStatus, string> = {
  Draft: "bg-muted text-muted-foreground",
  "Under Review": "bg-warning/15 text-warning",
  Approved: "bg-success/15 text-success",
  Failed: "bg-caution/15 text-caution",
};

export function StatusBadge({ status }: { status: ClaimStatus }) {
  return (
    <Badge variant="secondary" className={cn(STATUS_STYLES[status])}>
      {status}
    </Badge>
  );
}