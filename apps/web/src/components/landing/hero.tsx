import Link from "next/link"
import { ChevronDownIcon, ReceiptIcon } from "@/components/icons"
import { RecommendationHeader } from "@/components/audit/recommendation-header"
import { CheckStatusBadge, PriorityBadge } from "@/components/claims/status-badge"
import { Button } from "@/components/ui/button"
import TextLoop from "@/components/landing/text-loop"
import { HeroDotField } from "@/components/landing/hero-dot-field"
import { formatMoney } from "@/lib/format"

const CHECK_CHIPS = [
  { status: "passed", label: "Amounts" },
  { status: "passed", label: "Dates" },
  { status: "passed", label: "Duplicates" },
  { status: "failed", label: "Budget" },
] as const

function SampleAudit() {
  return (
    <div className="relative overflow-hidden rounded-2xl border bg-card p-5 shadow-[0_20px_50px_-30px_rgba(0,0,0,0.25)] dark:shadow-[0_20px_50px_-30px_rgba(0,0,0,0.7)]">
      <div
        aria-hidden
        className="pointer-events-none absolute -top-24 -right-24 size-56 rounded-full bg-primary/10 blur-3xl"
      />
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <ReceiptIcon className="size-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <p className="font-heading text-sm font-semibold">Claim #412</p>
              <PriorityBadge priority="medium" />
            </div>
            <p className="text-xs text-muted-foreground">
              Mayfair Residency, Bengaluru · 3 nights
            </p>
          </div>
        </div>
        <div className="text-right">
          <p className="font-mono text-lg font-semibold tabular-nums">
            {formatMoney("12900", "INR")}
          </p>
          <p className="text-xs text-muted-foreground">Accommodation</p>
        </div>
      </div>

      <div className="mt-4">
        <RecommendationHeader decision="review" confidence={0.62} priority={null} />
      </div>

      <div className="mt-4 grid gap-1.5">
        {CHECK_CHIPS.map((chip) => (
          <div
            key={chip.label}
            className="flex items-center justify-between rounded-lg border border-border/60 bg-muted/40 px-3 py-1.5"
          >
            <span className="text-xs font-medium">{chip.label}</span>
            <CheckStatusBadge status={chip.status} />
          </div>
        ))}
      </div>

      <p className="mt-4 text-xs text-muted-foreground">
        Sample claim. Every finding links back to its evidence.
      </p>
    </div>
  )
}

export function Hero() {
  return (
    <section className="border-b">
      <div className="relative overflow-hidden">
        <div aria-hidden className="pointer-events-none absolute inset-0">
          <HeroDotField />
        </div>
        <div className="relative mx-auto grid min-h-[calc(100vh-9rem)] max-w-7xl items-center gap-12 px-6 pt-16 pb-16 md:min-h-[calc(100vh-5rem)] md:grid-cols-2 md:pt-20 md:pb-24 lg:pt-24">
        <div className="flex flex-col gap-6">
          <p className="text-xs font-medium tracking-[0.18em] text-primary uppercase">
            Decision support for auditors
          </p>
          <h1 className="max-w-2xl font-heading text-4xl leading-none font-semibold tracking-tight text-balance md:text-5xl">
            Decide expense claims in minutes, not meetings.
          </h1>
          <p className="max-w-md text-base leading-relaxed text-muted-foreground">
            Each claim is checked against its receipt, the business rules, and
            company policy before you ever see a recommendation.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button asChild size="lg" className="px-5">
              <Link href="/login">Sign in to review claims</Link>
            </Button>
            <Button asChild size="lg" variant="ghost" className="px-5">
              <Link href="#workflow">
                See how it works
                <ChevronDownIcon />
              </Link>
            </Button>
          </div>
        </div>

        <SampleAudit />
      </div>
      </div>

      <div className="relative h-20 w-full overflow-hidden border-t md:h-24" aria-hidden>
        <TextLoop
          text="Verified · Grounded · Decided"
          shape="wave"
          separator="✦"
          speed={90}
          direction="forward"
          curviness={52}
          fontSize={30}
          fontWeight={600}
          letterSpacing={4}
          uppercase
          color="var(--primary-foreground)"
          ribbon
          ribbonColor="var(--primary)"
          ribbonWidth={58}
          pauseOnHover
        />
      </div>
    </section>
  )
}