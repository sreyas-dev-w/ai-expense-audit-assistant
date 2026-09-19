import Link from "next/link"
import { Button } from "@/components/ui/button"

export function Cta() {
  return (
    <section className="border-t">
      <div className="mx-auto flex max-w-7xl flex-col items-center gap-6 px-6 py-20 text-center md:py-24">
        <h2 className="max-w-2xl font-heading text-3xl leading-tight font-semibold tracking-tight text-balance md:text-4xl">
          Put the next claim batch through a grounded audit.
        </h2>
        <p className="max-w-xl text-base leading-relaxed text-muted-foreground">
          Sign in to review claims, approvals and policy documents end to end with a
          demo account.
        </p>
        <Button asChild size="lg" className="px-5">
          <Link href="/login">Sign in to review claims</Link>
        </Button>
        <p className="text-xs text-muted-foreground">
          Demo accounts <span className="font-mono">emp001</span> through{" "}
          <span className="font-mono">emp032</span>, password{" "}
          <span className="font-mono">password@123</span>.
        </p>
      </div>
    </section>
  )
}