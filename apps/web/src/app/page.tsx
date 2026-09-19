import { SiteHeader } from "@/components/landing/site-header"
import { Hero } from "@/components/landing/hero"
import { ImpactStrip } from "@/components/landing/impact-strip"
import { Workflow } from "@/components/landing/workflow"
import { ValidationSection } from "@/components/landing/validation-section"
import { PolicySection } from "@/components/landing/policy-section"
import { DecisionSection } from "@/components/landing/decision-section"
import { SecuritySection } from "@/components/landing/security-section"
import { Faq } from "@/components/landing/faq"
import { Cta } from "@/components/landing/cta"
import { SiteFooter } from "@/components/landing/site-footer"

export default function HomePage() {
  return (
    <div className="flex min-h-[100dvh] flex-col">
      <SiteHeader />
      <main className="flex-1">
        <Hero />
        <ImpactStrip />
        <Workflow />
        <ValidationSection />
        <PolicySection />
        <DecisionSection />
        <SecuritySection />
        <Faq />
        <Cta />
      </main>
      <SiteFooter />
    </div>
  )
}