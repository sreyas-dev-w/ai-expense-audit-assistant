"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { CheckIcon, RotateCcwIcon, XIcon } from "@/components/icons"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { FormField } from "@/components/form-field"
import { useUpdateClaimAudit } from "@/hooks/use-claims"
import { useSession } from "@/hooks/use-session"
import { ApiError } from "@/lib/api/client"
import type { ClaimDetailsResponse, ClaimPriority, ClaimStatus } from "@/lib/types/api"

const PRIORITIES: ClaimPriority[] = ["low", "medium", "high", "urgent"]

export function DecisionForm({ claim }: { claim: ClaimDetailsResponse }) {
  const router = useRouter()
  const auditerId = useSession((state) => state.employee?.employee_id)
  const [priority, setPriority] = React.useState<ClaimPriority>(claim.priority as ClaimPriority)
  const [notes, setNotes] = React.useState(claim.auditer_notes ?? "")
  const [pendingStatus, setPendingStatus] = React.useState<ClaimStatus | null>(null)
  const updateAudit = useUpdateClaimAudit()

  const isDecided = claim.status === "approved" || claim.status === "rejected"

  async function decide(status: ClaimStatus) {
    if (!auditerId) return
    setPendingStatus(status)
    try {
      await updateAudit.mutateAsync({
        claimId: claim.claim_id,
        data: { status, priority, auditer_id: auditerId, auditer_notes: notes || null },
      })
      toast.success(`Claim #${claim.claim_id} marked ${status.replace("_", " ")}`)
      router.push("/approvals")
    } catch (err) {
      toast.error("Could not record the decision", {
        description: err instanceof ApiError ? err.message : "Please try again.",
      })
    } finally {
      setPendingStatus(null)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Auditor decision</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {isDecided && (
          <p className="rounded-lg bg-muted/50 px-3 py-2 text-sm text-muted-foreground">
            This claim was already marked {claim.status.replace("_", " ")}. Submitting again
            will overwrite the previous decision and notes.
          </p>
        )}

        <FormField label="Priority" htmlFor="priority">
          <Select value={priority} onValueChange={(value) => setPriority(value as ClaimPriority)}>
            <SelectTrigger id="priority" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PRIORITIES.map((p) => (
                <SelectItem key={p} value={p}>
                  {p.charAt(0).toUpperCase() + p.slice(1)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        <FormField
          label="Notes for the record"
          htmlFor="auditer_notes"
          hint="Visible to the employee and future reviewers"
        >
          <Textarea
            id="auditer_notes"
            rows={4}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add context for this decision"
          />
        </FormField>

        <div className="flex flex-wrap items-center justify-between gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={updateAudit.isPending}
            onClick={() => decide("needs_revision")}
          >
            <RotateCcwIcon />
            {pendingStatus === "needs_revision" ? "Sending back…" : "Request changes"}
          </Button>

          <div className="flex gap-2">
            <Button
              type="button"
              variant="destructive"
              disabled={updateAudit.isPending}
              onClick={() => decide("rejected")}
            >
              <XIcon />
              {pendingStatus === "rejected" ? "Rejecting…" : "Reject"}
            </Button>
            <Button
              type="button"
              disabled={updateAudit.isPending}
              onClick={() => decide("approved")}
            >
              <CheckIcon />
              {pendingStatus === "approved" ? "Approving…" : "Approve"}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
