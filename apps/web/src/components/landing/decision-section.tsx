import {
  CircleCheckIcon,
  DocumentValidationIcon,
  FileSearchIcon,
  InfoIcon,
  RotateCcwIcon,
  ScaleIcon,
  TriangleAlertIcon,
} from "@/components/icons"
import { SectionHeading } from "@/components/landing/section-heading"

const DECISION_ITEMS = [
  {
    icon: CircleCheckIcon,
    label: "Recommendation",
    note: "Approve, reject, or needs review.",
  },
  {
    icon: InfoIcon,
    label: "Reasons",
    note: "The decision in plain language.",
  },
  {
    icon: DocumentValidationIcon,
    label: "Validation findings",
    note: "Which rule fired, and the evidence.",
  },
  {
    icon: FileSearchIcon,
    label: "Policy findings",
    note: "Each violation, with its citation.",
  },
  {
    icon: ScaleIcon,
    label: "Grounding references",
    note: "The retrieved policy passages.",
  },
  {
    icon: TriangleAlertIcon,
    label: "Warnings",
    note: "Budget left, authenticity flags.",
  },
  {
    icon: RotateCcwIcon,
    label: "Confidence",
    note: "The model's stated uncertainty.",
  },
]

export function DecisionSection() {
  return (
    <section className="border-t bg-muted/30">
      <div className="mx-auto grid max-w-7xl gap-12 px-6 py-20 md:grid-cols-2 md:items-start md:py-24">
        <div>
          <SectionHeading
            title="A recommendation an auditor can defend."
            description="The final result is decision support for the auditor or manager, not an autonomous approval. Every part of it can be traced back to evidence."
          />
          <div className="mt-8 rounded-2xl border bg-background p-5">
            <div className="flex gap-3">
              <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-warning/10 text-warning">
                <TriangleAlertIcon className="size-4.5" />
              </span>
              <div>
                <p className="font-heading text-sm font-semibold">
                  If the assessment call fails
                </p>
                <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                  The run degrades gracefully. A deterministic aggregation builds
                  the result from the validation and policy findings, and the audit
                  still completes with decision support instead of failing.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div>
          <p className="font-heading text-sm font-semibold">
            What the final result carries
          </p>
          <ul className="mt-4 flex flex-col divide-y divide-border/70 rounded-2xl border bg-card px-5">
            {DECISION_ITEMS.map((item, i) => (
              <li
                key={item.label}
                className="flex items-center gap-4 py-3.5 first:pt-5 last:pb-5"
              >
                <span
                  className={`flex size-9 shrink-0 items-center justify-center rounded-lg ${
                    i < 3 ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground"
                  }`}
                >
                  <item.icon className="size-4.5" />
                </span>
                <div className="flex flex-1 items-center justify-between gap-4">
                  <p className="text-sm font-medium">{item.label}</p>
                  <p className="text-right text-xs text-muted-foreground">{item.note}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}