import {
  EncryptIcon,
  FingerprintIcon,
  LockKeyIcon,
  ScaleIcon,
  FileValidationIcon,
  ClockIcon,
} from "@/components/icons"
import { SectionHeading } from "@/components/landing/section-heading"

const GROUPS: {
  title: string
  items: {
    icon: typeof LockKeyIcon
    title: string
    body: string
  }[]
}[] = [
  {
    title: "Least privilege, by design",
    items: [
      {
        icon: LockKeyIcon,
        title: "Agents never touch SQL",
        body: "They work through narrow, well-defined tools. No agent opens a raw database session, and there is no execute_sql tool.",
      },
      {
        icon: FingerprintIcon,
        title: "LLM output is untrusted",
        body: "Every model response passes Pydantic validation before it is accepted, so malformed output becomes an explicit error, not a silent pass.",
      },
      {
        icon: EncryptIcon,
        title: "No secrets in code",
        body: "All configuration is environment-driven. Credentials never reach the repository or the frontend.",
      },
    ],
  },
  {
    title: "Failures you can see",
    items: [
      {
        icon: FileValidationIcon,
        title: "Structured contracts",
        body: "Agents exchange Pydantic models, never loose dicts or free-form strings. The schema is defined once and reused.",
      },
      {
        icon: ClockIcon,
        title: "Explicit timeouts and retries",
        body: "Every external call has a timeout, and failures land as first-class workflow states with enough context to retry safely.",
      },
      {
        icon: ScaleIcon,
        title: "Short transactions",
        body: "Database work commits in deliberate short transactions. No transaction is held open across an LLM call.",
      },
    ],
  },
]

export function SecuritySection() {
  return (
    <section id="security" className="scroll-mt-20 border-t">
      <div className="mx-auto max-w-7xl px-6 py-20 md:py-24">
        <SectionHeading
          title="Built for finance review, not demo-day."
          description="The same discipline that makes the audit explainable also makes it safe to run on real employee data."
        />

        <div className="mt-10 grid gap-px overflow-hidden rounded-2xl border bg-border md:grid-cols-2">
          {GROUPS.map((group) => (
            <div key={group.title} className="flex flex-col bg-background p-6">
              <p className="font-heading text-sm font-semibold">{group.title}</p>
              <ul className="mt-4 flex flex-col divide-y divide-border/70">
                {group.items.map((item) => (
                  <li key={item.title} className="flex gap-3.5 py-4 first:pt-0 last:pb-0">
                    <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                      <item.icon className="size-4.5" />
                    </span>
                    <div>
                      <p className="text-sm font-medium">{item.title}</p>
                      <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                        {item.body}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}