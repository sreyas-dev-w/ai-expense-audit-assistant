import { FileIcon, ImageOffIcon } from "@/components/icons"
import { Button } from "@/components/ui/button"

/**
 * `receipt_url` is a path relative to the API process's filesystem
 * (`storage_dump/receipts/...`) with no static mount or download route, so
 * the receipt cannot be rendered here. This card is an honest placeholder
 * rather than a broken image.
 */
export function ReceiptCard({ receiptUrl }: { receiptUrl: string | null }) {
  const filename = receiptUrl?.split("/").pop() ?? null

  return (
    <div className="flex items-center gap-3 rounded-xl bg-muted/50 p-4 ring-1 ring-foreground/10">
      <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
        {filename ? <FileIcon className="size-4.5" /> : <ImageOffIcon className="size-4.5" />}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{filename ?? "No receipt on file"}</p>
        <p className="text-xs text-muted-foreground">
          Receipt preview is not available yet, the API does not serve stored files.
        </p>
      </div>
      <Button variant="outline" size="sm" disabled>
        View receipt
      </Button>
    </div>
  )
}
