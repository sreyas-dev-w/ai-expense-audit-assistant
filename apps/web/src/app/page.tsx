import Link from "next/link"
import {
  ClipboardCheckIcon,
  FileSearchIcon,
  ScaleIcon,
  ShieldCheckIcon,
} from "@/components/icons"
import { Button } from "@/components/ui/button"
import { RecommendationHeader } from "@/components/audit/recommendation-header"

const CAPABILITIES = [
  {
    icon: FileSearchIcon,
    title: "Structured claim review",
    description:
      "Every claim, receipt and line item in one place, organised by category with no spreadsheet cross-checking.",
  },
  {
    icon: ShieldCheckIcon,
    title: "Grounded validation",
    description:
      "Deterministic checks on totals, dates, duplicates and budget, with the evidence behind every finding.",
  },
  {
    icon: ScaleIcon,
    title: "Policy citations",
    description:
      "Recommendations reference the exact policy passages retrieved for that claim, not a black-box score.",
  },
]

export default function HomePage() {
  return (
    <div className="flex min-h-[100dvh] flex-col">
      <header className="flex h-16 items-center justify-between border-b px-6">
        <div className="flex items-center gap-2">
          <div className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <ClipboardCheckIcon className="size-4" />
          </div>
          <span className="font-heading text-sm font-semibold">Expense Audit</span>
        </div>
        <Button asChild size="sm">
          <Link href="/login">Sign in</Link>
        </Button>
      </header>

      <main className="flex-1">
        <section className="mx-auto grid max-w-6xl gap-10 px-6 py-20 md:grid-cols-2 md:items-center md:py-28">
          <div className="flex flex-col gap-6">
            <h1 className="max-w-lg text-4xl leading-tight font-semibold tracking-tight md:text-5xl">
              Decide expense claims in minutes, not meetings.
            </h1>
            <p className="max-w-md text-base leading-relaxed text-muted-foreground">
              A multi-agent workflow validates each claim against receipts, business
              rules and company policy, then hands the auditor a grounded
              recommendation instead of a pile of documents to reconcile by hand.
            </p>
            <div className="flex gap-3">
              <Button asChild size="lg">
                <Link href="/login">Sign in to review claims</Link>
              </Button>
            </div>
          </div>

          <RecommendationHeader decision="review" confidence={0.62} priority="medium" />
        </section>

        <section className="border-t bg-muted/30 px-6 py-16">
          <div className="mx-auto grid max-w-6xl gap-8 md:grid-cols-3">
            {CAPABILITIES.map((item) => (
              <div key={item.title} className="flex flex-col gap-3">
                <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <item.icon className="size-4.5" />
                </div>
                <h2 className="font-heading text-sm font-semibold">{item.title}</h2>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {item.description}
                </p>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="border-t px-6 py-6 text-center text-xs text-muted-foreground">
        AI Expense Audit Assistant. Decision support for auditors, not autonomous approval.
      </footer>
    </div>
  )
}
