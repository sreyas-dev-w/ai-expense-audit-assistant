"use client"

import * as React from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { FileIcon, FileTextIcon, ImageOffIcon } from "@/components/icons"
import { Button } from "@/components/ui/button"
import { receiptFileUrl } from "@/lib/api/client"

function isPdf(path: string) {
  return /\.pdf$/i.test(path)
}

function isImage(path: string) {
  return /\.(jpe?g|png|gif|webp|bmp)$/i.test(path)
}

function ReceiptThumbnail({ url, filename }: { url: string; filename: string }) {
  const [failed, setFailed] = React.useState(false)

  if (failed) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <FileIcon className="size-8" />
      </div>
    )
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element -- receipt preview URL
    <img
      src={url}
      alt={`${filename} preview`}
      onError={() => setFailed(true)}
      className="h-full w-full object-contain"
    />
  )
}

export function ReceiptCard({ receiptUrl }: { receiptUrl: string | null }) {
  const filename = receiptUrl?.split("/").pop() ?? null
  const url = receiptFileUrl(receiptUrl)

  if (!url) {
    return (
      <div className="flex items-center gap-3 rounded-xl bg-muted/50 p-4 ring-1 ring-foreground/10">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
          <ImageOffIcon className="size-4.5" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">No receipt on file</p>
          <p className="text-xs text-muted-foreground">
            This claim has no receipt attached to it.
          </p>
        </div>
      </div>
    )
  }

  const pdf = isPdf(receiptUrl!)
  const image = !pdf && isImage(receiptUrl!)

  return (
    <div className="rounded-xl bg-muted/50 p-4 ring-1 ring-foreground/10">
      <div className="mb-3 flex items-center gap-3">
        <div className="h-28 flex-1 overflow-hidden rounded-lg border border-input bg-background">
          {pdf ? (
            <div className="flex h-full items-center justify-center text-muted-foreground">
              <FileTextIcon className="size-8" />
            </div>
          ) : image ? (
            <ReceiptThumbnail
              key={url}
              url={url}
              filename={filename ?? "receipt"}
            />
          ) : (
            <div className="flex h-full items-center justify-center text-muted-foreground">
              <FileIcon className="size-8" />
            </div>
          )}
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium">{filename}</p>
          <p className="text-xs text-muted-foreground">Receipt attached to claim</p>
        </div>
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="outline" size="sm">
              View receipt
            </Button>
          </DialogTrigger>
          <DialogContent className="max-h-[calc(100dvh-2rem)] overflow-y-auto sm:max-w-3xl">
            <DialogHeader>
              <DialogTitle>{filename}</DialogTitle>
            </DialogHeader>
            {pdf ? (
              <iframe
                src={url}
                title={`${filename} preview`}
                className="h-[70vh] max-h-[70vh] w-full rounded-lg border border-input"
              />
            ) : (
              // eslint-disable-next-line @next/next/no-img-element -- receipt preview URL
              <img
                src={url}
                alt={`${filename} preview`}
                className="mx-auto max-h-[70vh] w-full rounded-lg border border-input object-contain"
              />
            )}
          </DialogContent>
        </Dialog>
      </div>
    </div>
  )
}