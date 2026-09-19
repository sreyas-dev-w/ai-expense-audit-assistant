import {
  CheckmarkBadgeIcon,
  DnaIcon,
  FileValidationIcon,
  GavelIcon,
  ReceiptIcon,
  ReceiptTextIcon,
  UserGroupIcon,
} from "@/components/icons"
import { SectionHeading } from "@/components/landing/section-heading"

interface WorkflowStep {
  title: string
  body: string
  parallel?: boolean
}

const STEPS: WorkflowStep[] = [
  {
    title: "Submit the claim",
    body: "The employee files the claim with its receipt. Four categories are covered: food and meals, travel, accommodation, and other.",
  },
  {
    title: "Extract the receipt",
    body: "OCR reads the receipt into structured line items, amounts and dates, so the auditor works with data, not scans.",
  },
  {
    title: "Validate and check policy",
    body: "The Validation Agent and the Policy RAG Agent run in the same step. Because they share one superstep, both halves finish in roughly half the wall-clock time.",
    parallel: true,
  },
  {
    title: "Recommend",
    body: "The assessment LLM summarises the two stage results into a recommendation with reasons, priority and confidence.",
  },
  {
    title: "Decide",
    body: "The auditor reviews the grounded recommendation and keeps the final call. Approval stays a human decision.",
  },
]

function ParallelBadge() {
  return (
    <span className="inline-flex w-fit items-center gap-1 rounded-md bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary">
      <DnaIcon className="size-3.5" />
      runs in parallel
    </span>
  )
}

function PipelineDiagram() {
  return (
    <div className="flex flex-col items-stretch gap-2 rounded-2xl border bg-card p-5">
      <p className="font-heading text-sm font-semibold">The pipeline in one view</p>

      <div className="flex items-center gap-3 rounded-xl border border-border/60 bg-muted/40 px-3 py-2.5">
        <span className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <ReceiptIcon className="size-4.5" />
        </span>
        <span className="text-sm">Claim + receipt</span>
      </div>
      <ArrowDown />
      <div className="flex items-center gap-3 rounded-xl border border-border/60 bg-muted/40 px-3 py-2.5">
        <span className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <ReceiptTextIcon className="size-4.5" />
        </span>
        <span className="text-sm">OCR and extraction</span>
      </div>
      <ArrowDown />
      <div className="rounded-xl bg-primary/5 p-3 ring-1 ring-primary/10">
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs font-medium text-primary">Fan out, run together</p>
          <ParallelBadge />
        </div>
        <div className="mt-2.5 grid gap-2 sm:grid-cols-2">
          <div className="flex items-center gap-2 rounded-lg border border-border/60 bg-background px-3 py-2">
            <FileValidationIcon className="size-4 text-primary" />
            <span className="text-xs font-medium">Validation rules</span>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-border/60 bg-background px-3 py-2">
            <GavelIcon className="size-4 text-primary" />
            <span className="text-xs font-medium">Policy retrieval</span>
          </div>
        </div>
      </div>
      <ArrowDown />
      <div className="flex items-center gap-3 rounded-xl border border-border/60 bg-muted/40 px-3 py-2.5">
        <span className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <CheckmarkBadgeIcon className="size-4.5" />
        </span>
        <span className="text-sm">LLM assessment</span>
      </div>
      <ArrowDown />
      <div className="flex items-center gap-3 rounded-xl border border-border/60 bg-muted/40 px-3 py-2.5">
        <span className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <UserGroupIcon className="size-4.5" />
        </span>
        <span className="text-sm">Auditor / manager</span>
      </div>
    </div>
  )
}

function ArrowDown() {
  return <div aria-hidden className="mx-auto h-4 w-px bg-border" />
}

export function Workflow() {
  return (
    <section id="workflow" className="scroll-mt-20 border-t">
      <div className="mx-auto grid max-w-7xl gap-12 px-6 py-20 md:grid-cols-2 md:items-start md:py-24">
        <div>
          <SectionHeading
            eyebrow="How it works"
            title="One submission, five accountable steps."
            description="The workflow is sequential end to end, with a single deliberate parallel fan-out where it saves the most time."
          />

          <ol className="mt-10 flex flex-col">
            {STEPS.map((step, i) => (
              <li key={step.title} className="grid grid-cols-[2.5rem_1fr] gap-4">
                <div className="flex flex-col items-center">
                  <span className="flex size-8 items-center justify-center rounded-full border border-border bg-background font-mono text-xs font-medium">
                    0{i + 1}
                  </span>
                  {i < STEPS.length - 1 && <span aria-hidden className="mt-2 w-px flex-1 bg-border" />}
                </div>
                <div className={i < STEPS.length - 1 ? "pb-8" : undefined}>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-heading text-base font-semibold">{step.title}</h3>
                    {step.parallel && <ParallelBadge />}
                  </div>
                  <p className="mt-1 max-w-md text-sm leading-relaxed text-muted-foreground">
                    {step.body}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </div>

        <div className="lg:sticky lg:top-24">
          <PipelineDiagram />
          <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
            The parallel fan-out is the only concurrency in the workflow. Everything
            else is a single forward pass from submission to recommendation.
          </p>
        </div>
      </div>
    </section>
  )
}