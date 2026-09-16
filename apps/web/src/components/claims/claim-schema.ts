import { z } from "zod";

import type { CategoryData, ClaimCreatePayload, Currency } from "@/lib/types";

/**
 * The option values below are not cosmetic: the OCR agent re-validates them
 * against fixed literals in `apps/api/app/agents/ocr_agent.py`, so a label may
 * change but a value may not.
 */
export const MEAL_TYPES = ["VEG", "NON_VEG", "MIXED"] as const;
export const TRAVEL_TYPES = ["FLIGHT", "TRAIN", "BUS", "CAR", "BIKE"] as const;
export const TRAVEL_CLASSES = ["ECONOMY_CLASS", "BUSINESS_CLASS"] as const;

export const RECEIPT_MIME_TYPES = ["image/png", "image/jpeg", "application/pdf"];

const required = (label: string) => `${label} is required`;

/**
 * One flat shape with a `superRefine` pass rather than a discriminated union,
 * because react-hook-form keeps a single field registry across category
 * switches. Only the selected category's fields are enforced.
 */
export const claimFormSchema = z
  .object({
    category: z.enum(["TRAVEL", "FOOD_MEALS", "ACCOMMODATION", "OTHER"]),
    business_purpose: z.string().trim().min(1, required("Business purpose")),
    merchant_name: z.string().trim().optional(),
    project_code: z.string().trim().optional(),
    claim_amount: z
      .string()
      .trim()
      .min(1, required("Amount"))
      .refine((v) => Number(v) > 0, "Amount must be greater than 0"),
    currency: z.string().min(1),

    // FOOD_MEALS
    meal_type: z.string().optional(),
    food_merchant_name: z.string().trim().optional(),
    number_of_people: z.string().optional(),

    // TRAVEL
    travel_type: z.string().optional(),
    origin: z.string().trim().optional(),
    destination: z.string().trim().optional(),
    travel_date: z.string().optional(),
    travel_class: z.string().optional(),
    ticket_number: z.string().trim().optional(),

    // ACCOMMODATION
    hotel_name: z.string().trim().optional(),
    location: z.string().trim().optional(),
    check_in: z.string().optional(),
    check_out: z.string().optional(),
    no_of_rooms: z.string().optional(),
    room_type: z.string().trim().optional(),

    // OTHER
    expense_type: z.string().trim().optional(),
    additional_details: z.string().trim().optional(),
  })
  .superRefine((values, ctx) => {
    const fail = (path: string, message: string) =>
      ctx.addIssue({ code: "custom", path: [path], message });

    const positiveInt = (raw: string | undefined, path: string, label: string) => {
      if (!raw) return fail(path, required(label));
      const parsed = Number(raw);
      if (!Number.isInteger(parsed) || parsed < 1) {
        fail(path, `${label} must be a whole number of at least 1`);
      }
    };

    if (values.category === "FOOD_MEALS") {
      if (!values.meal_type) fail("meal_type", required("Meal type"));
      if (!values.food_merchant_name) {
        fail("food_merchant_name", required("Restaurant name"));
      }
      positiveInt(values.number_of_people, "number_of_people", "Number of people");
    }

    if (values.category === "TRAVEL") {
      if (!values.travel_type) fail("travel_type", required("Travel type"));
      if (!values.origin) fail("origin", required("Origin"));
      if (!values.destination) fail("destination", required("Destination"));
      if (!values.travel_date) fail("travel_date", required("Travel date"));
      // Optional in the claim contract, but the OCR agent rejects a blank class.
      if (!values.travel_class) fail("travel_class", required("Travel class"));
    }

    if (values.category === "ACCOMMODATION") {
      if (!values.hotel_name) fail("hotel_name", required("Hotel name"));
      if (!values.location) fail("location", required("Location"));
      if (!values.check_in) fail("check_in", required("Check-in date"));
      if (!values.check_out) fail("check_out", required("Check-out date"));
      if (
        values.check_in &&
        values.check_out &&
        nightsBetween(values.check_in, values.check_out) < 1
      ) {
        fail("check_out", "Check-out must be after check-in");
      }
      positiveInt(values.no_of_rooms, "no_of_rooms", "Number of rooms");
      if (!values.room_type) fail("room_type", required("Room type"));
    }

    if (values.category === "OTHER") {
      if (!values.expense_type) fail("expense_type", required("Expense type"));
      if (values.additional_details) {
        try {
          const parsed = JSON.parse(values.additional_details);
          if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
            fail("additional_details", "Must be a JSON object");
          }
        } catch {
          fail("additional_details", "Must be valid JSON, for example {\"vendor\":\"Acme\"}");
        }
      }
    }
  });

export type ClaimFormValues = z.infer<typeof claimFormSchema>;

export function nightsBetween(checkIn: string, checkOut: string): number {
  const start = new Date(checkIn);
  const end = new Date(checkOut);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return 0;
  return Math.round((end.getTime() - start.getTime()) / 86_400_000);
}

export const claimFormDefaults: ClaimFormValues = {
  category: "TRAVEL",
  business_purpose: "",
  merchant_name: "",
  project_code: "",
  claim_amount: "",
  currency: "INR",
  meal_type: "",
  food_merchant_name: "",
  number_of_people: "",
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
  no_of_rooms: "",
  room_type: "",
  expense_type: "",
  additional_details: "",
};

function toCategoryData(values: ClaimFormValues): CategoryData {
  switch (values.category) {
    case "FOOD_MEALS":
      return {
        meal_type: values.meal_type!,
        merchant_name: values.food_merchant_name!,
        number_of_people: Number(values.number_of_people),
      };
    case "TRAVEL":
      return {
        travel_type: values.travel_type!,
        origin: values.origin!,
        destination: values.destination!,
        travel_date: values.travel_date!,
        travel_class: values.travel_class || null,
        ticket_number: values.ticket_number || null,
      };
    case "ACCOMMODATION":
      return {
        hotel_name: values.hotel_name!,
        location: values.location!,
        check_in: values.check_in!,
        check_out: values.check_out!,
        // The OCR agent recomputes this from the dates and rejects a mismatch.
        number_of_nights: nightsBetween(values.check_in!, values.check_out!),
        no_of_rooms: Number(values.no_of_rooms),
        room_type: values.room_type!,
      };
    case "OTHER":
      return {
        expense_type: values.expense_type!,
        merchant_name: values.merchant_name || null,
        additional_details: values.additional_details
          ? JSON.parse(values.additional_details)
          : null,
      };
  }
}

/** Build the exact `ClaimCreate` body the backend's discriminated union expects. */
export function toClaimPayload(
  values: ClaimFormValues,
  employeeId: string,
): ClaimCreatePayload {
  const merchant =
    values.category === "FOOD_MEALS"
      ? values.food_merchant_name
      : values.category === "ACCOMMODATION"
        ? values.hotel_name
        : values.merchant_name;

  return {
    employee_id: employeeId,
    business_purpose: values.business_purpose,
    merchant_name: merchant || null,
    project_code: values.project_code || null,
    claim_amount: values.claim_amount,
    currency: values.currency as Currency,
    category: values.category,
    category_data: toCategoryData(values),
  };
}
