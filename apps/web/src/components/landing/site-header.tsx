import Link from "next/link"
import { ClipboardCheckIcon } from "@/components/icons"
import { Button } from "@/components/ui/button"

const NAV_LINKS = [
  { href: "#workflow", label: "Workflow" },
  { href: "#validation", label: "Validation" },
  { href: "#policy", label: "Policy" },
  { href: "#security", label: "Security" },
  { href: "#faq", label: "FAQ" },
]

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-6">
        <Link href="/" className="flex items-center gap-2.5" aria-label="Expense Audit home">
          <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <ClipboardCheckIcon className="size-4.5" />
          </span>
          <span className="font-heading text-base font-semibold tracking-tight">
            Expense Audit
          </span>
        </Link>

        <nav className="hidden items-center gap-6 md:flex" aria-label="Primary">
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <Button asChild size="sm" variant="outline">
          <Link href="/login">Sign in</Link>
        </Button>
      </div>
    </header>
  )
}