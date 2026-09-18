import { ClaimForm } from "@/components/claims/claim-form"

export default function NewClaimPage() {
  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div>
        <h1 className="font-heading text-xl font-semibold">New claim</h1>
        <p className="text-sm text-muted-foreground">
          Enter the claim details and attach a receipt. The AI audit starts automatically once
          you submit.
        </p>
      </div>
      <ClaimForm />
    </div>
  )
}
