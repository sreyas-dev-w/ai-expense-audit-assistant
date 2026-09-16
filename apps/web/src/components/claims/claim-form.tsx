"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2Icon } from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "@/components/auth-provider";
import { CategoryFields } from "@/components/claims/category-fields";
import {
  RECEIPT_MIME_TYPES,
  claimFormDefaults,
  claimFormSchema,
  toClaimPayload,
  type ClaimFormValues,
} from "@/components/claims/claim-schema";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { CATEGORY_OPTIONS, CURRENCY_OPTIONS } from "@/lib/types";

type Stage = "idle" | "saving" | "auditing";

export function ClaimForm() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { profile } = useAuth();
  const [receipt, setReceipt] = useState<File | null>(null);
  const [receiptError, setReceiptError] = useState<string | null>(null);
  const [stage, setStage] = useState<Stage>("idle");
  const [error, setError] = useState<string | null>(null);

  const form = useForm<ClaimFormValues>({
    resolver: zodResolver(claimFormSchema),
    defaultValues: claimFormDefaults,
  });

  const category = form.watch("category");
  const errors = form.formState.errors;

  function handleReceipt(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    if (file && !RECEIPT_MIME_TYPES.includes(file.type)) {
      setReceipt(null);
      setReceiptError("Receipt must be a PNG, JPEG, or PDF file");
      return;
    }
    setReceiptError(null);
    setReceipt(file);
  }

  async function onSubmit(values: ClaimFormValues) {
    if (!profile) return;
    if (!receipt) {
      setReceiptError("A receipt is required so the audit workflow can run");
      return;
    }

    setError(null);
    setStage("saving");
    try {
      const claim = await api.createClaim(
        toClaimPayload(values, profile.employee_id),
        receipt,
      );

      // The claim exists now; the audit runs separately so a slow LLM pass
      // never blocks the submission.
      setStage("auditing");
      toast.success(`Claim #${claim.claim_id} submitted`, {
        description: "Running the audit workflow on the receipt.",
      });

      try {
        await api.runAudit(claim.claim_id);
        toast.success(`Audit complete for claim #${claim.claim_id}`);
      } catch (auditError) {
        toast.warning(`Claim #${claim.claim_id} saved, but the audit failed`, {
          description:
            auditError instanceof Error ? auditError.message : "Unknown error",
        });
      }

      await queryClient.invalidateQueries({ queryKey: ["claims"] });
      router.push("/claims");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not file the claim");
      setStage("idle");
    }
  }

  const busy = stage !== "idle";

  return (
    <Card>
      <CardHeader>
        <CardTitle>New expense claim</CardTitle>
        <CardDescription>
          Attach the receipt and the assistant will extract, validate, and check
          it against company policy after you submit.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={form.handleSubmit(onSubmit)} className="grid gap-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="grid gap-2">
              <Label htmlFor="category">Category</Label>
              <Select
                value={category}
                onValueChange={(next) =>
                  form.setValue("category", next as ClaimFormValues["category"], {
                    shouldValidate: false,
                  })
                }
              >
                <SelectTrigger id="category" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CATEGORY_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="project_code">Project code</Label>
              <Input
                id="project_code"
                placeholder={profile?.project_code ?? "Optional"}
                {...form.register("project_code")}
              />
              <p className="text-muted-foreground text-xs">
                Leave blank to use your assigned project.
              </p>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="claim_amount">Amount</Label>
              <Input
                id="claim_amount"
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
                {...form.register("claim_amount")}
              />
              {errors.claim_amount ? (
                <p className="text-destructive text-xs">
                  {errors.claim_amount.message}
                </p>
              ) : null}
            </div>

            <div className="grid gap-2">
              <Label htmlFor="currency">Currency</Label>
              <Select
                value={form.watch("currency")}
                onValueChange={(next) => form.setValue("currency", next)}
              >
                <SelectTrigger id="currency" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CURRENCY_OPTIONS.map((option) => (
                    <SelectItem key={option} value={option}>
                      {option}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid gap-2">
            <Label htmlFor="business_purpose">Business purpose</Label>
            <Textarea
              id="business_purpose"
              rows={3}
              placeholder="Client workshop travel for the Q3 migration engagement"
              {...form.register("business_purpose")}
            />
            {errors.business_purpose ? (
              <p className="text-destructive text-xs">
                {errors.business_purpose.message}
              </p>
            ) : null}
          </div>

          <Separator />
          <CategoryFields form={form} />
          <Separator />

          <div className="grid gap-2">
            <Label htmlFor="receipt">Receipt</Label>
            <Input
              id="receipt"
              type="file"
              accept=".png,.jpg,.jpeg,.pdf"
              onChange={handleReceipt}
            />
            <p className="text-muted-foreground text-xs">
              PNG, JPEG, or PDF. Required &mdash; the audit workflow reads it.
            </p>
            {receiptError ? (
              <p className="text-destructive text-xs">{receiptError}</p>
            ) : null}
          </div>

          {error ? (
            <Alert variant="destructive">
              <AlertTitle>Could not submit</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}

          <div className="flex items-center gap-3">
            <Button type="submit" disabled={busy}>
              {busy ? <Loader2Icon className="size-4 animate-spin" /> : null}
              {stage === "saving"
                ? "Saving claim..."
                : stage === "auditing"
                  ? "Running audit..."
                  : "Submit claim"}
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={busy}
              onClick={() => router.push("/claims")}
            >
              Cancel
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
