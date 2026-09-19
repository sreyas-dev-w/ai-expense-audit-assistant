import Link from "next/link"
import { ClipboardCheckIcon } from "@/components/icons"

const FOOTER_LINKS = [
  { href: "/claims", label: "Claims" },
  { href: "/approvals", label: "Approvals" },
  { href: "/policy", label: "Policy" },
  { href: "/login", label: "Sign in" },
]

export function SiteFooter() {
  return (
    <footer className="border-t px-6 py-8">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 text-center md:flex-row md:text-left">
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <span className="flex size-6 items-center justify-center rounded-md bg-primary/10 text-primary">
            <ClipboardCheckIcon className="size-3.5" />
          </span>
          <span className="font-heading font-semibold text-foreground">Expense Audit</span>
          · AI Expense Audit Assistant
        </p>

        <nav className="flex items-center gap-5" aria-label="Footer">
          {FOOTER_LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-sm text-muted-foreground transition-colors hover:text-foreground"
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <p className="text-xs text-muted-foreground">
          Decision support for auditors, not autonomous approval.
        </p>
      </div>
    </footer>
  )
}