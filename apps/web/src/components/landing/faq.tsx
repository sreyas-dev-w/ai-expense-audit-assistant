import { SectionHeading } from "@/components/landing/section-heading"

const FAQS = [
  {
    q: "Can the AI approve or reject a claim on its own?",
    a: "No. It produces a recommendation, reasons, findings and references for the auditor to review. This is decision support, not autonomous approval.",
  },
  {
    q: "What happens when the policy store has no matching policy?",
    a: "Retrieval with empty or below-threshold context is flagged as insufficient context, not failed. No unsupported policy claim is ever presented as authoritative.",
  },
  {
    q: "What if the recommendation model is unavailable?",
    a: "The run degrades gracefully. A deterministic aggregation builds the result from the validation and policy findings, and the audit still completes.",
  },
  {
    q: "How are duplicate claims caught?",
    a: "Exact and fuzzy scoring against the employee's prior claims, using document number, merchant, amount and date within a 7-day window, up to a 100-claim scan.",
  },
  {
    q: "Which expense categories are covered?",
    a: "Food and meals, travel, accommodation, and other. Each category gets its own structured extraction and its own policy evaluation.",
  },
  {
    q: "Who sees the recommendation?",
    a: "The auditor and manager reviewing the claim. The final decision-support record is persisted so it can be revisited after a decision is made.",
  },
]

export function Faq() {
  return (
    <section id="faq" className="scroll-mt-20 border-t bg-muted/30">
      <div className="mx-auto max-w-7xl px-6 py-20 md:py-24">
        <SectionHeading
          title="Questions reviewers actually ask."
          description="Straight answers about who decides, what happens when a stage fails, and where the evidence lives."
        />

        <dl className="mt-10 grid gap-x-12 gap-y-8 md:grid-cols-2">
          {FAQS.map((faq) => (
            <div key={faq.q} className="border-l-2 border-primary/25 pl-4">
              <dt className="font-heading text-base font-semibold text-balance">{faq.q}</dt>
              <dd className="mt-2 text-sm leading-relaxed text-muted-foreground">{faq.a}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  )
}