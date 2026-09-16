"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2Icon } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import type { ClaimDecision } from "@/lib/types";

const COPY: Record<
  ClaimDecision,
  { title: string; description: string; action: string }
> = {
  approve: {
    title: "Approve this claim",
    description:
      "Your note is stored on the claim as the approval record. Explain what you checked.",
    action: "Approve claim",
  },
  reject: {
    title: "Reject this claim",
    description:
      "Your note is stored on the claim and tells the employee why it was rejected.",
    action: "Reject claim",
  },
};

export function DecisionDialog({
  claimId,
  decision,
  disabled,
}: {
  claimId: number;
  decision: ClaimDecision;
  disabled?: boolean;
}) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [notes, setNotes] = useState("");
  const copy = COPY[decision];

  const mutation = useMutation({
    mutationFn: () => api.decideClaim(claimId, decision, notes.trim()),
    onSuccess: async () => {
      toast.success(
        decision === "approve"
          ? `Claim #${claimId} approved`
          : `Claim #${claimId} rejected`,
      );
      setOpen(false);
      setNotes("");
      await queryClient.invalidateQueries({ queryKey: ["claims"] });
    },
    onError: (error) =>
      toast.error("Could not record the decision", {
        description: error instanceof Error ? error.message : undefined,
      }),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          variant={decision === "approve" ? "default" : "destructive"}
          disabled={disabled}
        >
          {copy.action}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{copy.title}</DialogTitle>
          <DialogDescription>{copy.description}</DialogDescription>
        </DialogHeader>
        <div className="grid gap-2">
          <Label htmlFor={`notes-${decision}`}>Decision notes</Label>
          <Textarea
            id={`notes-${decision}`}
            rows={4}
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="Receipt matches the claim and the amount is within the L3 travel cap."
          />
          <p className="text-muted-foreground text-xs">Required.</p>
        </div>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline">Cancel</Button>
          </DialogClose>
          <Button
            variant={decision === "approve" ? "default" : "destructive"}
            disabled={!notes.trim() || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? (
              <Loader2Icon className="size-4 animate-spin" />
            ) : null}
            {copy.action}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
