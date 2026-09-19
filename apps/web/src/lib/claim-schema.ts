import { z } from "zod"

/**
 * Form-side validation schema. Mirrors `ClaimCreate` in
 * `apps/api/app/schemas/claim.py` + `apps/api/app/schemas/expense.py`.
 *
 * Deliberately flat rather than a `z.discriminatedUnion`: react-hook-form's
 * generic inference does not carry a union type cleanly through
 * `useForm`/`Control`/`FieldErrors` (the resolver and form instance end up
 * structurally incompatible across branches). Conditional requirements are
 * enforced with `superRefine` instead, and `claim-form.tsx` maps the flat
 * shape onto the correct `ClaimCreate` variant before submitting.
 *
 * Numeric fields stay as `z.string()` (matching what an uncontrolled HTML
 * input actually holds) rather than `z.coerce.number()` — coercion gives the
 * schema a different input/output type, which `zodResolver`/`useForm` then
 * can't reconcile into one form-values type. Values are parsed with
 * `Number(...)` where needed instead.
 */

function isPositiveNumber(value: string): boolean {
  const n = Number(value)
  return value.trim() !== "" && Number.isFinite(n) && n > 0
}

function isPositiveInt(value: string): boolean {
  const n = Number(value)
  return value.trim() !== "" && Number.isInteger(n) && n >= 1
}

export const CATEGORIES = ["FOOD_MEALS", "TRAVEL", "ACCOMMODATION", "OTHER"] as const
export type Category = (typeof CATEGORIES)[number]

export const CURRENCIES = ["INR", "USD", "EUR", "GBP", "AUD", "CAD", "JPY"] as const
export type CurrencyCode = (typeof CURRENCIES)[number]

const claimFormShape = z.object({
  category: z.enum(CATEGORIES),
  employee_id: z.string().min(1),
  project_code: z.string().nullable().optional(),
  business_purpose: z.string().max(500).nullable().optional(),
  merchant_name: z.string().max(255).nullable().optional(),
  claim_amount: z.string().refine(isPositiveNumber, "Claim amount must be greater than 0"),
  currency: z.enum(CURRENCIES),

  // FOOD_MEALS
  meal_type: z.string().nullable().optional(),
  number_of_people: z.string().nullable().optional(),

  // TRAVEL
  travel_type: z.string().nullable().optional(),
  origin: z.string().nullable().optional(),
  destination: z.string().nullable().optional(),
  travel_date: z.string().nullable().optional(),
  travel_class: z.string().nullable().optional(),
  ticket_number: z.string().nullable().optional(),

  // ACCOMMODATION
  hotel_name: z.string().nullable().optional(),
  location: z.string().nullable().optional(),
  check_in: z.string().nullable().optional(),
  check_out: z.string().nullable().optional(),
  number_of_nights: z.string().nullable().optional(),
  no_of_rooms: z.string().nullable().optional(),
  room_type: z.string().nullable().optional(),

  // OTHER
  expense_type: z.string().nullable().optional(),
})

interface IssueReporter {
  addIssue: (issue: { code: "custom"; message: string; path: string[] }) => void
}

function requireField(ctx: IssueReporter, value: unknown, path: string, message = "Required") {
  if (value === null || value === undefined || value === "") {
    ctx.addIssue({ code: "custom", message, path: [path] })
  }
}

function requirePositiveInt(ctx: IssueReporter, value: string | null | undefined, path: string, message: string) {
  if (!value || !isPositiveInt(value)) {
    ctx.addIssue({ code: "custom", message, path: [path] })
  }
}

export const claimFormSchema = claimFormShape.superRefine((values, ctx) => {
  switch (values.category) {
    case "FOOD_MEALS":
      requireField(ctx, values.meal_type, "meal_type")
      requirePositiveInt(ctx, values.number_of_people, "number_of_people", "At least 1 person")
      break
    case "TRAVEL":
      requireField(ctx, values.travel_type, "travel_type")
      requireField(ctx, values.origin, "origin")
      requireField(ctx, values.destination, "destination")
      requireField(ctx, values.travel_date, "travel_date")
      break
    case "ACCOMMODATION":
      requireField(ctx, values.hotel_name, "hotel_name")
      requireField(ctx, values.location, "location")
      requireField(ctx, values.check_in, "check_in")
      requireField(ctx, values.check_out, "check_out")
      requirePositiveInt(ctx, values.number_of_nights, "number_of_nights", "At least 1 night")
      requirePositiveInt(ctx, values.no_of_rooms, "no_of_rooms", "At least 1 room")
      break
    case "OTHER":
      requireField(ctx, values.expense_type, "expense_type")
      break
  }
})

export type ClaimFormValues = z.infer<typeof claimFormShape>

export const EXPENSE_CATEGORIES: { value: Category; label: string }[] = [
  { value: "FOOD_MEALS", label: "Meals" },
  { value: "TRAVEL", label: "Travel" },
  { value: "ACCOMMODATION", label: "Accommodation" },
  { value: "OTHER", label: "Other" },
]

export function buildDefaultValues(
  category: Category,
  employeeId: string,
  projectCode: string | null
): ClaimFormValues {
  return {
    category,
    employee_id: employeeId,
    project_code: projectCode,
    business_purpose: "",
    merchant_name: "",
    claim_amount: "0",
    currency: "INR",
    meal_type: "",
    number_of_people: "1",
    travel_type: "",
    origin: "",
    destination: "",
    travel_date: "",
    travel_class: "",
    ticket_number: "",
    hotel_name: "",
    location: "",
    check_in: "",
    check_out: "",
    number_of_nights: "1",
    no_of_rooms: "1",
    room_type: "",
    expense_type: "",
  }
}
