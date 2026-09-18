"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm, type UseFormReturn } from "react-hook-form"
import { Loader2Icon, UploadIcon } from "@/components/icons"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { FormField } from "@/components/form-field"
import { LineItemsField } from "@/components/claims/line-items-field"
import {
  CURRENCIES,
  EXPENSE_CATEGORIES,
  buildDefaultValues,
  claimFormSchema,
  type Category,
  type ClaimFormValues,
} from "@/lib/claim-schema"
import type { ClaimCreate } from "@/lib/types/api"
import { useSession } from "@/hooks/use-session"
import { useSubmitClaim } from "@/hooks/use-claims"
import { ApiError } from "@/lib/api/client"

function toClaimCreate(values: ClaimFormValues): ClaimCreate {
  const base = {
    employee_id: values.employee_id,
    business_purpose: values.business_purpose || null,
    merchant_name: values.merchant_name || null,
    project_code: values.project_code || null,
    claim_amount: values.claim_amount,
    currency: values.currency,
  }

  const lineItems = values.line_items.map((item) => ({
    item_header: item.item_header,
    item_amount: item.item_amount,
  }))

  // `superRefine` in claim-schema.ts guarantees the category-specific fields
  // below are non-empty by the time this runs; the `?? ""` / `?? "1"` fallbacks
  // only satisfy TypeScript's nullable field types.
  switch (values.category) {
    case "FOOD_MEALS":
      return {
        ...base,
        category: "FOOD_MEALS",
        category_data: {
          meal_type: values.meal_type ?? "",
          merchant_name: values.merchant_name ?? "",
          number_of_people: Number(values.number_of_people ?? "1"),
          line_items: lineItems,
        },
      }
    case "TRAVEL":
      return {
        ...base,
        category: "TRAVEL",
        category_data: {
          travel_type: values.travel_type ?? "",
          origin: values.origin ?? "",
          destination: values.destination ?? "",
          travel_date: values.travel_date ?? "",
          travel_class: values.travel_class || null,
          ticket_number: values.ticket_number || null,
          line_items: lineItems,
        },
      }
    case "ACCOMMODATION":
      return {
        ...base,
        category: "ACCOMMODATION",
        category_data: {
          hotel_name: values.hotel_name ?? "",
          location: values.location ?? "",
          check_in: values.check_in ?? "",
          check_out: values.check_out ?? "",
          number_of_nights: Number(values.number_of_nights ?? "1"),
          no_of_rooms: Number(values.no_of_rooms ?? "1"),
          room_type: values.room_type || null,
          line_items: lineItems,
        },
      }
    case "OTHER":
      return {
        ...base,
        category: "OTHER",
        category_data: {
          expense_type: values.expense_type ?? "",
          merchant_name: values.merchant_name || null,
          additional_details: null,
          line_items: lineItems,
        },
      }
  }
}

export function ClaimForm() {
  const router = useRouter()
  const employee = useSession((state) => state.employee)
  const submitClaim = useSubmitClaim()
  const [receipt, setReceipt] = React.useState<File | null>(null)
  const [receiptError, setReceiptError] = React.useState<string | null>(null)

  const form = useForm<ClaimFormValues>({
    resolver: zodResolver(claimFormSchema),
    defaultValues: buildDefaultValues("FOOD_MEALS", employee?.employee_id ?? "", employee?.project_code ?? null),
  })

  const category = form.watch("category")
  const lineItems = form.watch("line_items")

  // Claim amount auto-sums from line items but stays editable, so a manual
  // adjustment (e.g. after a discount) is not silently overwritten unless
  // the user changes a line item afterwards.
  React.useEffect(() => {
    const total = lineItems.reduce((sum, item) => sum + (Number(item.item_amount) || 0), 0)
    form.setValue("claim_amount", String(Math.round(total * 100) / 100), { shouldValidate: false })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(lineItems)])

  function handleCategoryChange(next: Category) {
    if (next === category) return
    form.reset(buildDefaultValues(next, employee?.employee_id ?? "", employee?.project_code ?? null))
  }

  async function onSubmit(values: ClaimFormValues) {
    if (!receipt) {
      setReceiptError("Attach a receipt to submit this claim.")
      return
    }
    setReceiptError(null)

    try {
      const claim = toClaimCreate(values)
      const result = await submitClaim.mutateAsync({ claim, receipt })
      toast.success(`Claim ${result.claim_id} submitted`, {
        description: "The AI audit is now running in the background.",
      })
      router.push("/claims")
    } catch (err) {
      toast.error("Could not submit the claim", {
        description: err instanceof ApiError ? err.message : "Please try again.",
      })
    }
  }

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-6" noValidate>
      <Card>
        <CardHeader>
          <CardTitle>Expense category</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <FormField label="Category" htmlFor="category">
            <Select value={category} onValueChange={(value) => handleCategoryChange(value as Category)}>
              <SelectTrigger id="category" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {EXPENSE_CATEGORIES.map((item) => (
                  <SelectItem key={item.value} value={item.value}>
                    {item.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>

          <div className="grid gap-4 md:grid-cols-2">
            <FormField
              label="Business purpose"
              htmlFor="business_purpose"
              error={form.formState.errors.business_purpose?.message}
            >
              <Textarea id="business_purpose" rows={2} {...form.register("business_purpose")} />
            </FormField>

            <FormField
              label="Merchant name"
              htmlFor="merchant_name"
              error={form.formState.errors.merchant_name?.message}
            >
              <Input id="merchant_name" {...form.register("merchant_name")} />
            </FormField>
          </div>

          <CategoryFields category={category} form={form} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Line items</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <LineItemsField form={form} />

          <div className="grid gap-4 md:grid-cols-2">
            <FormField
              label="Claim amount"
              htmlFor="claim_amount"
              hint="Auto-summed from line items, still editable"
              error={form.formState.errors.claim_amount?.message}
            >
              <Input
                id="claim_amount"
                type="number"
                step="0.01"
                className="font-mono tabular-nums"
                {...form.register("claim_amount")}
              />
            </FormField>

            <FormField label="Currency" htmlFor="currency">
              <Select
                value={form.watch("currency")}
                onValueChange={(value) => form.setValue("currency", value as ClaimFormValues["currency"])}
              >
                <SelectTrigger id="currency" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CURRENCIES.map((currency) => (
                    <SelectItem key={currency} value={currency}>
                      {currency}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Receipt</CardTitle>
        </CardHeader>
        <CardContent>
          <FormField label="Receipt file" htmlFor="receipt" error={receiptError ?? undefined} hint="PNG, JPEG or PDF">
            <label
              htmlFor="receipt"
              className="flex cursor-pointer items-center gap-3 rounded-lg border border-dashed border-input px-3 py-3 text-sm hover:bg-muted/50"
            >
              <UploadIcon className="size-4 text-muted-foreground" />
              <span className="text-muted-foreground">
                {receipt ? receipt.name : "Choose a file to upload"}
              </span>
            </label>
            <input
              id="receipt"
              type="file"
              accept="image/png,image/jpeg,application/pdf"
              className="sr-only"
              onChange={(e) => {
                setReceipt(e.target.files?.[0] ?? null)
                setReceiptError(null)
              }}
            />
          </FormField>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={() => router.push("/claims")}>
          Cancel
        </Button>
        <Button type="submit" disabled={submitClaim.isPending}>
          {submitClaim.isPending && <Loader2Icon className="animate-spin" />}
          Submit claim
        </Button>
      </div>
    </form>
  )
}

function CategoryFields({
  category,
  form,
}: {
  category: Category
  form: UseFormReturn<ClaimFormValues>
}) {
  const errors = form.formState.errors

  if (category === "FOOD_MEALS") {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        <FormField label="Meal type" htmlFor="meal_type" error={errors.meal_type?.message}>
          <Input id="meal_type" placeholder="Lunch, dinner, client meal" {...form.register("meal_type")} />
        </FormField>
        <FormField
          label="Number of people"
          htmlFor="number_of_people"
          error={errors.number_of_people?.message}
        >
          <Input id="number_of_people" type="number" min={1} {...form.register("number_of_people")} />
        </FormField>
      </div>
    )
  }

  if (category === "TRAVEL") {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        <FormField label="Travel type" htmlFor="travel_type" error={errors.travel_type?.message}>
          <Input id="travel_type" placeholder="Flight, train, cab" {...form.register("travel_type")} />
        </FormField>
        <FormField label="Travel date" htmlFor="travel_date" error={errors.travel_date?.message}>
          <Input id="travel_date" type="date" {...form.register("travel_date")} />
        </FormField>
        <FormField label="Origin" htmlFor="origin" error={errors.origin?.message}>
          <Input id="origin" {...form.register("origin")} />
        </FormField>
        <FormField label="Destination" htmlFor="destination" error={errors.destination?.message}>
          <Input id="destination" {...form.register("destination")} />
        </FormField>
        <FormField label="Travel class" htmlFor="travel_class">
          <Input id="travel_class" placeholder="Optional" {...form.register("travel_class")} />
        </FormField>
        <FormField label="Ticket number" htmlFor="ticket_number">
          <Input id="ticket_number" placeholder="Optional" {...form.register("ticket_number")} />
        </FormField>
      </div>
    )
  }

  if (category === "ACCOMMODATION") {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        <FormField label="Hotel name" htmlFor="hotel_name" error={errors.hotel_name?.message}>
          <Input id="hotel_name" {...form.register("hotel_name")} />
        </FormField>
        <FormField label="Location" htmlFor="location" error={errors.location?.message}>
          <Input id="location" {...form.register("location")} />
        </FormField>
        <FormField label="Check in" htmlFor="check_in" error={errors.check_in?.message}>
          <Input id="check_in" type="date" {...form.register("check_in")} />
        </FormField>
        <FormField label="Check out" htmlFor="check_out" error={errors.check_out?.message}>
          <Input id="check_out" type="date" {...form.register("check_out")} />
        </FormField>
        <FormField
          label="Number of nights"
          htmlFor="number_of_nights"
          error={errors.number_of_nights?.message}
        >
          <Input id="number_of_nights" type="number" min={1} {...form.register("number_of_nights")} />
        </FormField>
        <FormField label="Number of rooms" htmlFor="no_of_rooms" error={errors.no_of_rooms?.message}>
          <Input id="no_of_rooms" type="number" min={1} {...form.register("no_of_rooms")} />
        </FormField>
        <FormField label="Room type" htmlFor="room_type">
          <Input id="room_type" placeholder="Optional" {...form.register("room_type")} />
        </FormField>
      </div>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <FormField label="Expense type" htmlFor="expense_type" error={errors.expense_type?.message}>
        <Input id="expense_type" placeholder="Office supplies, software, other" {...form.register("expense_type")} />
      </FormField>
    </div>
  )
}
