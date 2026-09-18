import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ReceiptCard } from "@/components/claims/receipt-card"
import { formatDate, formatMoney, toTitleCase } from "@/lib/format"
import type { ClaimDetailsResponse } from "@/lib/types/api"

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  )
}

function categoryFields(claim: ClaimDetailsResponse): { label: string; value: React.ReactNode }[] {
  const data = claim.category_data as Record<string, unknown>

  switch (claim.category) {
    case "FOOD_MEALS":
      return [
        { label: "Meal type", value: String(data.meal_type ?? "-") },
        { label: "Merchant", value: String(data.merchant_name ?? "-") },
        { label: "Number of people", value: String(data.number_of_people ?? "-") },
      ]
    case "TRAVEL":
      return [
        { label: "Travel type", value: String(data.travel_type ?? "-") },
        { label: "Origin", value: String(data.origin ?? "-") },
        { label: "Destination", value: String(data.destination ?? "-") },
        { label: "Travel date", value: formatDate(data.travel_date as string) },
        ...(data.travel_class ? [{ label: "Class", value: String(data.travel_class) }] : []),
        ...(data.ticket_number ? [{ label: "Ticket number", value: String(data.ticket_number) }] : []),
      ]
    case "ACCOMMODATION":
      return [
        { label: "Hotel", value: String(data.hotel_name ?? "-") },
        { label: "Location", value: String(data.location ?? "-") },
        { label: "Check in", value: formatDate(data.check_in as string) },
        { label: "Check out", value: formatDate(data.check_out as string) },
        { label: "Nights", value: String(data.number_of_nights ?? "-") },
        { label: "Rooms", value: String(data.no_of_rooms ?? "-") },
      ]
    default:
      return [{ label: "Expense type", value: String(data.expense_type ?? "-") }]
  }
}

export function ClaimSummary({ claim }: { claim: ClaimDetailsResponse }) {
  const lineItems = (claim.category_data as { line_items?: { item_header: string; item_amount: string }[] })
    .line_items ?? []

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Claim details</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 md:grid-cols-3">
          <Field label="Category" value={toTitleCase(claim.category)} />
          <Field label="Claim amount" value={formatMoney(claim.claim_amount, claim.currency)} />
          <Field label="Business purpose" value={claim.business_purpose ?? "-"} />
          {categoryFields(claim).map((field) => (
            <Field key={field.label} label={field.label} value={field.value} />
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Line items</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y">
            {lineItems.map((item, i) => (
              <div key={i} className="flex items-center justify-between px-(--card-spacing) py-2.5 text-sm">
                <span>{item.item_header}</span>
                <span className="font-mono tabular-nums">
                  {formatMoney(item.item_amount, claim.currency)}
                </span>
              </div>
            ))}
            {lineItems.length === 0 && (
              <p className="px-(--card-spacing) py-4 text-sm text-muted-foreground">
                No line items recorded.
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      <ReceiptCard receiptUrl={claim.receipt_url} />
    </div>
  )
}
