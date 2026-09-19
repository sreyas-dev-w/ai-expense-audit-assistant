"use client"

import { FilePreview } from "@/components/file-preview"

export function ReceiptPreview({ file }: { file: File | null }) {
  return <FilePreview file={file} label="Receipt" />
}