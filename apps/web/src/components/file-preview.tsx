"use client"

import * as React from "react"

export function FilePreview({ file, label }: { file: File | null; label: string }) {
  const previewUrl = React.useMemo(() => (file ? URL.createObjectURL(file) : null), [file])

  React.useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl)
    }
  }, [previewUrl])

  if (!file || !previewUrl) return null

  if (file.type === "application/pdf") {
    return (
      <div className="overflow-hidden rounded-lg border border-input">
        <iframe src={previewUrl} title={`${label} preview`} className="h-96 w-full" />
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-lg border border-input bg-muted/50">
      {/* eslint-disable-next-line @next/next/no-img-element -- local object URL preview */}
      <img
        src={previewUrl}
        alt={`${label} preview`}
        className="mx-auto max-h-96 w-full object-contain"
      />
    </div>
  )
}