"use client";

import type { UseFormReturn } from "react-hook-form";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { titleCase } from "@/lib/format";
import {
  MEAL_TYPES,
  TRAVEL_CLASSES,
  TRAVEL_TYPES,
  nightsBetween,
  type ClaimFormValues,
} from "@/components/claims/claim-schema";

type Form = UseFormReturn<ClaimFormValues>;

function Field({
  label,
  htmlFor,
  error,
  hint,
  children,
}: {
  label: string;
  htmlFor: string;
  error?: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid gap-2">
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
      {hint && !error ? (
        <p className="text-muted-foreground text-xs">{hint}</p>
      ) : null}
      {error ? <p className="text-destructive text-xs">{error}</p> : null}
    </div>
  );
}

/** A controlled Select bound to a react-hook-form field. */
function SelectField({
  form,
  name,
  label,
  placeholder,
  options,
}: {
  form: Form;
  name: keyof ClaimFormValues;
  label: string;
  placeholder: string;
  options: readonly string[];
}) {
  const value = form.watch(name) as string | undefined;
  const error = form.formState.errors[name]?.message as string | undefined;

  return (
    <Field label={label} htmlFor={name} error={error}>
      <Select
        value={value || undefined}
        onValueChange={(next) =>
          form.setValue(name, next, { shouldValidate: true })
        }
      >
        <SelectTrigger id={name} className="w-full">
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {options.map((option) => (
            <SelectItem key={option} value={option}>
              {titleCase(option)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </Field>
  );
}

export function CategoryFields({ form }: { form: Form }) {
  const { register, formState, watch } = form;
  const errors = formState.errors;
  const category = watch("category");

  if (category === "FOOD_MEALS") {
    return (
      <div className="grid gap-4 sm:grid-cols-2">
        <SelectField
          form={form}
          name="meal_type"
          label="Meal type"
          placeholder="Select meal type"
          options={MEAL_TYPES}
        />
        <Field
          label="Restaurant name"
          htmlFor="food_merchant_name"
          error={errors.food_merchant_name?.message}
        >
          <Input id="food_merchant_name" {...register("food_merchant_name")} />
        </Field>
        <Field
          label="Number of people"
          htmlFor="number_of_people"
          error={errors.number_of_people?.message}
        >
          <Input
            id="number_of_people"
            type="number"
            min={1}
            {...register("number_of_people")}
          />
        </Field>
      </div>
    );
  }

  if (category === "TRAVEL") {
    return (
      <div className="grid gap-4 sm:grid-cols-2">
        <SelectField
          form={form}
          name="travel_type"
          label="Travel type"
          placeholder="Select travel type"
          options={TRAVEL_TYPES}
        />
        <SelectField
          form={form}
          name="travel_class"
          label="Travel class"
          placeholder="Select travel class"
          options={TRAVEL_CLASSES}
        />
        <Field label="Origin" htmlFor="origin" error={errors.origin?.message}>
          <Input id="origin" placeholder="Bengaluru" {...register("origin")} />
        </Field>
        <Field
          label="Destination"
          htmlFor="destination"
          error={errors.destination?.message}
        >
          <Input id="destination" placeholder="Mumbai" {...register("destination")} />
        </Field>
        <Field
          label="Travel date"
          htmlFor="travel_date"
          error={errors.travel_date?.message}
        >
          <Input id="travel_date" type="date" {...register("travel_date")} />
        </Field>
        <Field
          label="Ticket number"
          htmlFor="ticket_number"
          error={errors.ticket_number?.message}
          hint="Optional"
        >
          <Input id="ticket_number" {...register("ticket_number")} />
        </Field>
      </div>
    );
  }

  if (category === "ACCOMMODATION") {
    const checkIn = watch("check_in");
    const checkOut = watch("check_out");
    const nights = checkIn && checkOut ? nightsBetween(checkIn, checkOut) : 0;

    return (
      <div className="grid gap-4 sm:grid-cols-2">
        <Field
          label="Hotel name"
          htmlFor="hotel_name"
          error={errors.hotel_name?.message}
        >
          <Input id="hotel_name" {...register("hotel_name")} />
        </Field>
        <Field
          label="Location"
          htmlFor="location"
          error={errors.location?.message}
        >
          <Input id="location" placeholder="Mumbai" {...register("location")} />
        </Field>
        <Field
          label="Check-in"
          htmlFor="check_in"
          error={errors.check_in?.message}
        >
          <Input id="check_in" type="date" {...register("check_in")} />
        </Field>
        <Field
          label="Check-out"
          htmlFor="check_out"
          error={errors.check_out?.message}
        >
          <Input id="check_out" type="date" {...register("check_out")} />
        </Field>
        <Field
          label="Nights"
          htmlFor="number_of_nights"
          hint="Derived from the dates above"
        >
          <Input id="number_of_nights" value={nights || ""} readOnly disabled />
        </Field>
        <Field
          label="Number of rooms"
          htmlFor="no_of_rooms"
          error={errors.no_of_rooms?.message}
        >
          <Input
            id="no_of_rooms"
            type="number"
            min={1}
            {...register("no_of_rooms")}
          />
        </Field>
        <Field
          label="Room type"
          htmlFor="room_type"
          error={errors.room_type?.message}
        >
          <Input id="room_type" placeholder="Deluxe" {...register("room_type")} />
        </Field>
      </div>
    );
  }

  return (
    <div className="grid gap-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field
          label="Expense type"
          htmlFor="expense_type"
          error={errors.expense_type?.message}
        >
          <Input
            id="expense_type"
            placeholder="Office supplies"
            {...register("expense_type")}
          />
        </Field>
        <Field
          label="Merchant"
          htmlFor="merchant_name"
          error={errors.merchant_name?.message}
          hint="Optional"
        >
          <Input id="merchant_name" {...register("merchant_name")} />
        </Field>
      </div>
      <Field
        label="Additional details"
        htmlFor="additional_details"
        error={errors.additional_details?.message}
        hint='Optional JSON object, for example {"vendor":"Acme","invoice":"INV-12"}'
      >
        <Textarea
          id="additional_details"
          rows={3}
          className="font-mono text-xs"
          {...register("additional_details")}
        />
      </Field>
    </div>
  );
}
