const FACTS = [
  {
    value: "Half the latency",
    label: "Validation rules and policy review run in one parallel step.",
  },
  {
    value: "90 days",
    label: "Claim-age window enforced by the date rules, with no exceptions.",
  },
  {
    value: "100 claims",
    label: "Prior claims scanned for duplicates, exact and fuzzy, per review.",
  },
  {
    value: "₹1.00",
    label: "Total-to-invoice tolerance before an amount is flagged on a claim.",
  },
]

export function ImpactStrip() {
  return (
    <section aria-label="Product facts" className="py-14">
      <div className="mx-auto grid max-w-7xl grid-cols-1 gap-px overflow-hidden rounded-2xl border bg-border px-0 sm:grid-cols-2 lg:grid-cols-4">
        {FACTS.map((fact) => (
          <div key={fact.value} className="flex flex-col gap-2 bg-background p-6">
            <p className="font-mono text-2xl font-semibold tracking-tight tabular-nums">
              {fact.value}
            </p>
            <p className="max-w-[32ch] text-sm leading-relaxed text-muted-foreground">
              {fact.label}
            </p>
          </div>
        ))}
      </div>
    </section>
  )
}