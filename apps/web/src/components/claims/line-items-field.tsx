"use client"

import { PlusIcon, Trash2Icon } from "@/components/icons"
import { useFieldArray, type UseFormReturn } from "react-hook-form"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import type { ClaimFormValues } from "@/lib/claim-schema"

export function LineItemsField({ form }: { form: UseFormReturn<ClaimFormValues> }) {
  const { control, register } = form
  const { fields, append, remove } = useFieldArray({
    control,
    name: "line_items",
  })

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <Label>Line items</Label>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => append({ item_header: "", item_amount: "" })}
        >
          <PlusIcon /> Add item
        </Button>
      </div>

      <div className="flex flex-col gap-2">
        {fields.map((field, index) => (
          <div key={field.id} className="flex items-start gap-2">
            <Input
              placeholder="Item description"
              className="flex-1"
              {...register(`line_items.${index}.item_header`)}
            />
            <Input
              type="number"
              step="0.01"
              placeholder="Amount"
              className="w-32"
              {...register(`line_items.${index}.item_amount`)}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              disabled={fields.length === 1}
              onClick={() => remove(index)}
              aria-label="Remove line item"
            >
              <Trash2Icon />
            </Button>
          </div>
        ))}
      </div>

      {fields.length === 0 && (
        <p className="text-xs text-muted-foreground">Add at least one line item.</p>
      )}
    </div>
  )
}
