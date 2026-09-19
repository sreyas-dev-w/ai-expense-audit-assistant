import type { ComponentType } from "react"
import {
  CalendarIcon,
  CopyIcon,
  DocumentValidationIcon,
  FingerprintIcon,
  ReceiptIndianRupeeIcon,
  WalletIcon,
} from "@/components/icons"
import { SectionHeading } from "@/components/landing/section-heading"
import { CheckStatusBadge, SeverityBadge } from "@/components/claims/status-badge"

const RULES: {
  icon: ComponentType<{ className?: string }>
  title: string
  desc: string
  iconBox: string
  chip?: React.ReactNode
}[] = [
  {
    icon: ReceiptIndianRupeeIcon,
    title: "Amounts",
    desc: "The claimed total must match the extracted lines and the invoice. Rows off by more than ₹1.00 are flagged with the figures used in the comparison.",
    iconBox: "bg-primary/10 text-primary",
    chip: <CheckStatusBadge status="failed" />,
  },
  {
    icon: CalendarIcon,
    title: "Dates",
    desc: "Dates must be present, valid and before the submission date. Claims older than 90 days are blocked, and a missing date is blocking except for accommodation.",
    iconBox: "bg-warning/10 text-warning",
  },
  {
    icon: DocumentValidationIcon,
    title: "Cross-field checks",
    desc: "A receipt is required where the category needs one, and the employee on the claim matches the submission before the review moves on.",
    iconBox: "bg-info/10 text-info",
  },
  {
    icon: WalletIcon,
    title: "Budget",
    desc: "Remaining account budget is loaded per review and checked against the claim. Exceeding it is a blocking finding, not a nudge.",
    iconBox: "bg-success/10 text-success",
  },
  {
    icon: CopyIcon,
    title: "Duplicates",
    desc: "Exact and fuzzy scoring against the prior 100 claims, using document number, merchant, amount and date within a 7-day window.",
    iconBox: "bg-destructive/10 text-destructive",
  },
  {
    icon: FingerprintIcon,
    title: "Authenticity",
    desc: "Not-a-receipt and missing-identifier heuristics flag suspicion and seed the reasoning pass. The reviewer can add warnings but never override a blocking finding to pass.",
    iconBox: "bg-muted text-foreground",
  },
]

const SEVERITIES: { severity: "blocking" | "warning" | "info"; meaning: string }[] = [
  { severity: "blocking", meaning: "Stops the claim from passing until resolved." },
  { severity: "warning", meaning: "Needs attention, can still be reviewed." },
  { severity: "info", meaning: "Context to consider before deciding." },
]

const VERDICTS = ["PASS", "FLAG_FOR_REVIEW", "FAIL"] as const

export function ValidationSection() {
  return (
    <section id="validation" className="scroll-mt-20 border-t bg-muted/30">
      <div className="mx-auto max-w-7xl px-6 py-20 md:py-24">
        <SectionHeading
          title="Deterministic rules decide. The model only reasons."
          description="Validation is coded, not prompted. Amounts, dates, duplicates and budget checks run as exact rules, and the verdict they produce is traceable line by line."
        />

        <div className="mt-10 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {RULES.map((rule) => (
            <div
              key={rule.title}
              className="flex flex-col gap-3 rounded-2xl border bg-background p-6 transition-transform active:scale-[0.99]"
            >
              <div className="flex items-center justify-between">
                <span
                  className={`flex size-10 items-center justify-center rounded-lg ${rule.iconBox}`}
                >
                  <rule.icon className="size-5" />
                </span>
                {rule.chip}
              </div>
              <h3 className="font-heading text-base font-semibold">{rule.title}</h3>
              <p className="text-sm leading-relaxed text-muted-foreground">{rule.desc}</p>
            </div>
          ))}
        </div>

        <div className="mt-8 grid gap-px overflow-hidden rounded-2xl border bg-border md:grid-cols-2">
          <div className="flex flex-col gap-3 bg-background p-6">
            <p className="font-heading text-sm font-semibold">Finding severity</p>
            <ul className="flex flex-col gap-2.5">
              {SEVERITIES.map((s) => (
                <li key={s.severity} className="flex items-center gap-3">
                  <SeverityBadge severity={s.severity} />
                  <span className="text-sm text-muted-foreground">{s.meaning}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="flex flex-col justify-center gap-3 bg-background p-6">
            <p className="font-heading text-sm font-semibold">Rule-chain verdict</p>
            <div className="flex flex-wrap gap-2">
              {VERDICTS.map((verdict) => (
                <span
                  key={verdict}
                  className="inline-flex h-5 items-center rounded-full border border-border bg-muted/50 px-2.5 font-mono text-xs font-medium text-muted-foreground"
                >
                  {verdict}
                </span>
              ))}
            </div>
            <p className="text-sm leading-relaxed text-muted-foreground">
              The chain resolves to one verdict for the auditor, alongside the
              individual findings behind it.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}