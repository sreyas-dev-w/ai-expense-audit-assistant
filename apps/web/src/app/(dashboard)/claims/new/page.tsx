"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Loader2, ShieldCheck, AlertTriangle, Sparkles } from "lucide-react";
import Link from "next/link";
import { api, formatCurrency } from "@/lib/api";
import type { SubmitResponse } from "@/lib/types";
import { useUser } from "@/hooks/use-user";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { FileUpload } from "@/components/file-upload";
import { StatusBadge } from "@/components/status-badge";

const claimSchema = z.object({
  claim_name: z
    .string()
    .min(3, "Claim name must be at least 3 characters.")
    .max(200, "Claim name is too long."),
  estimated_amount: z
    .number()
    .finite("Enter a numeric amount.")
    .positive("Amount must be greater than zero.")
    .max(100_000_000, "Amount exceeds the supported range."),
});

type ClaimFormValues = z.infer<typeof claimSchema>;

const CLAIM_EXAMPLES = [
  { label: "Client dinner", amount: "2500" },
  { label: "Flight — Mumbai → Delhi", amount: "18500" },
  { label: "Hotel — Bengaluru", amount: "32000" },
];

export default function NewClaimPage() {
  const { user } = useUser();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [document, setDocument] = React.useState<File | null>(null);
  const [submitResult, setSubmitResult] = React.useState<SubmitResponse | null>(null);
  const [submitError, setSubmitError] = React.useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<ClaimFormValues>({
    resolver: zodResolver(claimSchema),
    defaultValues: { claim_name: "" },
  });

  const mutation = useMutation({
    mutationFn: (values: ClaimFormValues) => {
      if (!user) throw new Error("No active user");
      if (!document) throw new Error("Please attach a receipt document.");
      const formData = new FormData();
      formData.append("employee_id", user.employee_id);
      formData.append("claim_name", values.claim_name);
      formData.append("estimated_amount", String(values.estimated_amount));
      formData.append("document", document);
      return api.submitClaim(formData);
    },
    onSuccess: (result) => {
      setSubmitResult(result);
      setSubmitError(null);
      queryClient.invalidateQueries({ queryKey: ["claims"] });
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
    },
    onError: (error: Error) => {
      setSubmitError(error.message);
      setSubmitResult(null);
    },
  });

  const onSubmit = handleSubmit((values) => mutation.mutate(values));

  return (
    <div className="mx-auto w-full max-w-4xl px-6 py-8">
      <div className="mb-6">
        <Link
          href="/claims"
          className="mb-4 inline-flex items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" /> Back to My Claims
        </Link>
        <h1 className="text-2xl font-semibold text-foreground">Create New Claim</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Submit an expense claim. The AI pipeline will OCR the receipt, validate it against
          the account budget, and route it for approval.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
        <Card>
          <CardHeader>
            <CardTitle>Claim details</CardTitle>
            <CardDescription>
              Fields are validated client-side before the multipart upload begins.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={onSubmit} className="flex flex-col gap-5">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="claim_name">Claim name</Label>
                <Input
                  id="claim_name"
                  placeholder="e.g. Business travel — Mumbai trip"
                  aria-invalid={!!errors.claim_name}
                  {...register("claim_name")}
                />
                {errors.claim_name && (
                  <p className="text-xs text-destructive">{errors.claim_name.message}</p>
                )}
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="estimated_amount">Estimated amount (INR)</Label>
                <div className="relative">
                  <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
                    ₹
                  </span>
                  <Input
                    id="estimated_amount"
                    type="number"
                    inputMode="decimal"
                    min="1"
                    step="any"
                    placeholder="0.00"
                    className="pl-7"
                    aria-invalid={!!errors.estimated_amount}
                    {...register("estimated_amount", { valueAsNumber: true })}
                  />
                </div>
                {errors.estimated_amount && (
                  <p className="text-xs text-destructive">{errors.estimated_amount.message}</p>
                )}
              </div>

              <div className="flex flex-col gap-1.5">
                <Label>Receipt document</Label>
                <div className="flex flex-wrap gap-2">
                  {CLAIM_EXAMPLES.map((example) => (
                    <button
                      key={example.label}
                      type="button"
                      onClick={() => {
                        setValue("claim_name", example.label, { shouldValidate: true });
                        setValue("estimated_amount", Number(example.amount), {
                          shouldValidate: true,
                        });
                      }}
                      className="rounded-md border border-border px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground"
                    >
                      {example.label} · ₹{example.amount}
                    </button>
                  ))}
                </div>
                <FileUpload value={document} onChange={setDocument} />
              </div>

              {submitError && (
                <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2.5 text-sm text-destructive">
                  <AlertTriangle className="mt-0.5 size-4 shrink-0" />
                  {submitError}
                </div>
              )}

              <div className="flex items-center justify-end gap-3 border-t border-border pt-4">
                <Button type="button" variant="ghost" onClick={() => router.push("/claims")}>
                  Cancel
                </Button>
                <Button type="submit" disabled={mutation.isPending} className="gap-1.5">
                  {mutation.isPending ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <Sparkles className="size-4" />
                  )}
                  {mutation.isPending ? "Running audit…" : "Submit for audit"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <div className="flex flex-col gap-4">
          <Card className="bg-card/60">
            <CardHeader>
              <CardTitle className="text-sm">Active user</CardTitle>
            </CardHeader>
            <CardContent className="text-sm">
              {user ? (
                <>
                  <p className="font-medium text-foreground">{user.employee_name}</p>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    {user.employee_id} · {user.job_level} · {user.project_code}
                  </p>
                  <Badge
                    variant={user.is_manager ? "secondary" : "outline"}
                    className={user.is_manager ? "bg-primary/15 text-primary" : undefined}
                  >
                    {user.is_manager ? "Manager" : "Contributor"}
                  </Badge>
                </>
              ) : (
                <p className="text-xs text-muted-foreground">Loading…</p>
              )}
            </CardContent>
          </Card>

          <Card className="bg-card/60">
            <CardHeader>
              <CardTitle className="text-sm">Audit pipeline</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2.5 text-xs text-muted-foreground">
              <PipelineStep step="1" label="OCR agent extracts merchant / date / total" />
              <PipelineStep step="2" label="Validation agent checks account budget" />
              <PipelineStep step="3" label="Policy agent runs compliance scan" />
            </CardContent>
          </Card>
        </div>
      </div>

      {submitResult && (
        <Card className="mt-6 border-border/60">
          <CardHeader>
            <div className="flex items-center gap-2">
              <ShieldCheck
                className={
                  submitResult.status === "Failed"
                    ? "size-5 text-caution"
                    : "size-5 text-primary"
                }
              />
              <CardTitle>Audit result</CardTitle>
            </div>
            <CardDescription>
              Workflow completed via the compiled LangGraph state machine.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4 text-sm">
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge status={submitResult.status} />
              <span className="text-muted-foreground">
                Claim #{submitResult.claim_id} · {formatCurrency(submitResult.ocr_text?.total_amount ?? 0)}
              </span>
              <span className="text-xs text-muted-foreground">{submitResult.message}</span>
            </div>

            <div className="grid gap-2 rounded-lg border border-border bg-input/20 p-3 text-xs sm:grid-cols-3">
              <div>
                <p className="text-muted-foreground">Merchant</p>
                <p className="mt-0.5 font-medium text-foreground">
                  {submitResult.ocr_text?.merchant ?? "—"}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">Date</p>
                <p className="mt-0.5 font-medium text-foreground">
                  {submitResult.ocr_text?.date ?? "—"}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">Total amount</p>
                <p className="mt-0.5 font-medium text-foreground">
                  {formatCurrency(submitResult.ocr_text?.total_amount ?? 0)}
                </p>
              </div>
            </div>

            {submitResult.violations.length > 0 && (
              <div className="flex flex-col gap-1.5 rounded-lg border border-caution/30 bg-caution/10 p-3 text-xs">
                <p className="font-medium text-caution">Violations</p>
                {submitResult.violations.map((violation) => (
                  <p key={violation} className="text-caution/90">
                    • {violation}
                  </p>
                ))}
              </div>
            )}

            <div className="flex justify-end">
              <Button variant="outline" onClick={() => router.push("/claims")}>
                View my claims
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function PipelineStep({ step, label }: { step: string; label: string }) {
  return (
    <div className="flex items-start gap-2">
      <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/15 text-[10px] font-semibold text-primary">
        {step}
      </span>
      <span>{label}</span>
    </div>
  );
}