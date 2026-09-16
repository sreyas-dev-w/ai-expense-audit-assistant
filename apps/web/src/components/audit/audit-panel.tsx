"use client";

import { RecommendationBadge } from "@/components/claims/status-badge";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { formatMoney, percent, titleCase } from "@/lib/format";
import type {
  AuditRunResponse,
  ValidationSeverity,
} from "@/lib/types";

const SEVERITY_VARIANT: Record<
  ValidationSeverity,
  React.ComponentProps<typeof Badge>["variant"]
> = {
  blocking: "destructive",
  warning: "secondary",
  info: "outline",
};

function BulletList({ items }: { items: string[] }) {
  if (!items.length) return null;
  return (
    <ul className="grid list-disc gap-1 pl-5 text-sm">
      {items.map((item, index) => (
        <li key={index}>{item}</li>
      ))}
    </ul>
  );
}

export function AuditPanel({ audit }: { audit: AuditRunResponse }) {
  const result = audit.audit_response ?? audit.output;
  const validation = audit.validation_response ?? result?.validation ?? null;
  const policy = audit.policy_response ?? result?.policy ?? null;

  if (!result && !validation && !policy) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Audit</CardTitle>
          <CardDescription>
            No audit has been recorded for this claim yet.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="grid gap-6">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle>Audit recommendation</CardTitle>
            {result ? (
              <RecommendationBadge recommendation={result.recommendation} />
            ) : null}
            <Badge variant="outline">
              Confidence {percent(audit.confidence_score ?? result?.confidence)}
            </Badge>
          </div>
          <CardDescription>
            Decision support only &mdash; the approval below is yours to make.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          {audit.notes ? (
            <p className="text-sm whitespace-pre-wrap">{audit.notes}</p>
          ) : null}

          {result?.reasons?.length ? (
            <div className="grid gap-2">
              <p className="text-sm font-medium">Reasons</p>
              <BulletList items={result.reasons} />
            </div>
          ) : null}

          {result?.warnings?.length ? (
            <Alert>
              <AlertTitle>Warnings</AlertTitle>
              <AlertDescription>
                <BulletList items={result.warnings} />
              </AlertDescription>
            </Alert>
          ) : null}

          {audit.error ? (
            <Alert variant="destructive">
              <AlertTitle>The audit run reported an error</AlertTitle>
              <AlertDescription>
                {audit.error.agent}: {audit.error.message}
              </AlertDescription>
            </Alert>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Validation</CardTitle>
          <CardDescription>
            Deterministic rule checks over the claim and the extracted receipt.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          {validation ? (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <Badge
                  variant={
                    validation.verdict === "PASS"
                      ? "default"
                      : validation.verdict === "FAIL"
                        ? "destructive"
                        : "secondary"
                  }
                >
                  {titleCase(validation.verdict)}
                </Badge>
                <Badge variant="outline">
                  Confidence {percent(validation.confidence)}
                </Badge>
              </div>

              {validation.summary ? (
                <p className="text-sm whitespace-pre-wrap">{validation.summary}</p>
              ) : null}

              {audit.validation_violation ? (
                <Alert variant="destructive">
                  <AlertTitle>Validation violations</AlertTitle>
                  <AlertDescription className="whitespace-pre-wrap">
                    {audit.validation_violation}
                  </AlertDescription>
                </Alert>
              ) : null}

              {validation.findings.length ? (
                <div className="grid gap-2">
                  <p className="text-sm font-medium">Findings</p>
                  <div className="grid gap-2">
                    {validation.findings.map((finding) => (
                      <div
                        key={`${finding.rule_id}-${finding.description}`}
                        className="rounded-md border p-3"
                      >
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant={SEVERITY_VARIANT[finding.severity]}>
                            {titleCase(finding.severity)}
                          </Badge>
                          <span className="font-mono text-xs">
                            {finding.rule_id}
                          </span>
                          <span className="text-muted-foreground text-xs">
                            {titleCase(finding.category)}
                          </span>
                        </div>
                        <p className="mt-2 text-sm">{finding.description}</p>
                        {finding.detail ? (
                          <p className="text-muted-foreground mt-1 text-xs">
                            {finding.detail}
                          </p>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              {validation.budget ? (
                <div className="grid gap-1 rounded-md border p-3 text-sm">
                  <p className="font-medium">Budget</p>
                  <p className="text-muted-foreground">
                    Account {validation.budget.account_id} has{" "}
                    {formatMoney(
                      validation.budget.remaining_budget,
                      validation.budget.currency ?? "INR",
                    )}{" "}
                    remaining against a claim of{" "}
                    {formatMoney(
                      validation.budget.claim_amount,
                      validation.budget.currency ?? "INR",
                    )}
                    .{" "}
                    {validation.budget.within_budget
                      ? "Within budget."
                      : "Over budget."}
                  </p>
                </div>
              ) : null}

              {validation.duplicate_candidates.length ? (
                <div className="grid gap-2">
                  <p className="text-sm font-medium">Possible duplicates</p>
                  <BulletList
                    items={validation.duplicate_candidates.map(
                      (candidate) =>
                        `Claim #${candidate.claim_id} (score ${candidate.score.toFixed(2)}): ${candidate.match_reasons.join(", ")}`,
                    )}
                  />
                </div>
              ) : null}

              {validation.warnings.length ? (
                <div className="grid gap-2">
                  <p className="text-sm font-medium">Warnings</p>
                  <BulletList items={validation.warnings} />
                </div>
              ) : null}

              {validation.checks.length ? (
                <Accordion type="single" collapsible>
                  <AccordionItem value="checks">
                    <AccordionTrigger className="text-sm">
                      All {validation.checks.length} rule checks
                    </AccordionTrigger>
                    <AccordionContent>
                      <div className="grid gap-1">
                        {validation.checks.map((check) => (
                          <div
                            key={check.check_name}
                            className="flex items-center justify-between gap-3 text-sm"
                          >
                            <span>{titleCase(check.check_name)}</span>
                            <Badge
                              variant={
                                check.status === "passed"
                                  ? "default"
                                  : check.status === "failed"
                                    ? "destructive"
                                    : "outline"
                              }
                            >
                              {titleCase(check.status)}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                </Accordion>
              ) : null}
            </>
          ) : (
            <p className="text-muted-foreground text-sm">
              No validation output was recorded.
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Policy</CardTitle>
          <CardDescription>
            Grounded against the ingested corporate expense policy.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          {policy ? (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <Badge
                  variant={
                    policy.decision === "APPROVE"
                      ? "default"
                      : policy.decision === "REJECT"
                        ? "destructive"
                        : "secondary"
                  }
                >
                  {titleCase(policy.decision)}
                </Badge>
                <Badge variant="outline">
                  Confidence {percent(policy.confidence)}
                </Badge>
              </div>

              {policy.summary ? (
                <p className="text-sm whitespace-pre-wrap">{policy.summary}</p>
              ) : null}

              {audit.policy_violation ? (
                <Alert variant="destructive">
                  <AlertTitle>Policy violations</AlertTitle>
                  <AlertDescription className="whitespace-pre-wrap">
                    {audit.policy_violation}
                  </AlertDescription>
                </Alert>
              ) : null}

              {policy.violations.length ? (
                <div className="grid gap-2">
                  <p className="text-sm font-medium">Violation detail</p>
                  {policy.violations.map((violation, index) => (
                    <div key={index} className="rounded-md border p-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant={SEVERITY_VARIANT[violation.severity]}>
                          {titleCase(violation.severity)}
                        </Badge>
                        {violation.policy_reference ? (
                          <span className="text-muted-foreground text-xs">
                            {violation.policy_reference}
                          </span>
                        ) : null}
                      </div>
                      <p className="mt-2 text-sm">{violation.description}</p>
                      {violation.detail ? (
                        <p className="text-muted-foreground mt-1 text-xs">
                          {violation.detail}
                        </p>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : null}

              {policy.reasons.length ? (
                <div className="grid gap-2">
                  <p className="text-sm font-medium">Reasons</p>
                  <BulletList items={policy.reasons} />
                </div>
              ) : null}

              {policy.references.length ? (
                <Accordion type="single" collapsible>
                  <AccordionItem value="references">
                    <AccordionTrigger className="text-sm">
                      {policy.references.length} policy excerpts used
                    </AccordionTrigger>
                    <AccordionContent>
                      <div className="grid gap-3">
                        {policy.references.map((reference) => (
                          <div key={reference.chunk_id}>
                            <p className="text-muted-foreground text-xs">
                              Chunk {reference.chunk_id}
                              {reference.similarity_score
                                ? ` · similarity ${reference.similarity_score.toFixed(2)}`
                                : ""}
                            </p>
                            <p className="mt-1 text-sm">{reference.content}</p>
                            <Separator className="mt-3" />
                          </div>
                        ))}
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                </Accordion>
              ) : null}
            </>
          ) : (
            <p className="text-muted-foreground text-sm">
              No policy output was recorded.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
