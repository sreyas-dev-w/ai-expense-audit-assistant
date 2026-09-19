import { DatabaseIcon, FolderCheckIcon, GavelIcon } from "@/components/icons"
import { GroundingReferences } from "@/components/audit/grounding-references"
import { SectionHeading } from "@/components/landing/section-heading"
import type { PolicyReference } from "@/lib/types/api"

const ANCHOR_POINTS = [
  {
    icon: GavelIcon,
    title: "Cites the source, not a score",
    body: "Each policy finding carries the document name, the chunk it came from and its similarity score. No black box.",
  },
  {
    icon: FolderCheckIcon,
    title: "Retrieved from real policy files",
    body: "Policies live as documents in the knowledge base and are searched with vector retrieval, not hardcoded rules.",
  },
  {
    icon: DatabaseIcon,
    title: "No context means no claim",
    body: "When retrieval comes up empty or below threshold, the review is flagged as having insufficient context rather than failing, so no rule is ever invented.",
  },
]

const SAMPLE_REFERENCES: PolicyReference[] = [
  {
    chunk_id: 41,
    policy_id: 2,
    policy_filename: "travel-policy-v2.pdf",
    content:
      "Business class is permitted for flights over eight hours for job level L5 and above. Premium economy is the default for all other long-haul segments.",
    similarity_score: 0.83,
  },
]

export function PolicySection() {
  return (
    <section id="policy" className="scroll-mt-20 border-t">
      <div className="mx-auto grid max-w-7xl gap-12 px-6 py-20 md:grid-cols-2 md:items-start md:py-24">
        <div>
          <SectionHeading
            eyebrow="Policy grounding"
            title="The recommendation cites the exact policy passage."
            description="Evaluation is grounded in the policy content retrieved for that specific claim. Unsupported claims are never presented as authoritative."
          />

          <ul className="mt-10 flex flex-col">
            {ANCHOR_POINTS.map((point, i) => (
              <li
                key={point.title}
                className={`flex gap-4 ${i < ANCHOR_POINTS.length - 1 ? "border-b border-border/70 pb-6" : ""} ${i > 0 ? "pt-6" : ""}`}
              >
                <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <point.icon className="size-5" />
                </span>
                <div>
                  <h3 className="font-heading text-base font-semibold">{point.title}</h3>
                  <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                    {point.body}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div className="lg:sticky lg:top-24">
          <div className="rounded-2xl border bg-card p-5">
            <p className="mb-4 text-xs font-medium tracking-[0.14em] text-muted-foreground uppercase">
              Sample citation
            </p>
            <GroundingReferences references={SAMPLE_REFERENCES} />
          </div>
          <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
            What an auditor expands with a click: the policy document, the chunk,
            and how closely it matched the claim at retrieval time.
          </p>
        </div>
      </div>
    </section>
  )
}