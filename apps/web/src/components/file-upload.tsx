"use client";

import * as React from "react";
import { CloudUpload, FileImage, FileText, X } from "lucide-react";
import { cn } from "cn";

const ACCEPTED_MIME = [
  "image/png",
  "image/jpeg",
  "image/webp",
  "application/pdf",
];

export interface UploadedFile {
  file: File;
}

interface FileUploadProps {
  value: File | null;
  onChange: (file: File | null) => void;
}

export function FileUpload({ value, onChange }: FileUploadProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const acceptFile = (file: File | undefined | null) => {
    setError(null);
    if (!file) return;
    if (!ACCEPTED_MIME.includes(file.type)) {
      setError("Only PNG, JPEG, WebP and PDF files are accepted.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError("File exceeds the 10 MB upload limit.");
      return;
    }
    onChange(file);
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    acceptFile(event.dataTransfer.files?.[0]);
  };

  const isImage = value?.type.startsWith("image/") ?? false;

  return (
    <div className="flex flex-col gap-2">
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload claim document"
        onClick={() => inputRef.current?.click()}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragOver={(event) => {
          event.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={cn(
          "group flex min-h-40 cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed bg-input/20 px-6 text-center transition-colors",
          isDragging
            ? "border-primary bg-primary/10"
            : "border-border hover:border-primary/50 hover:bg-input/30"
        )}
      >
        <div
          className={cn(
            "flex size-11 items-center justify-center rounded-xl transition-colors",
            isDragging ? "bg-primary/20 text-primary" : "bg-muted text-muted-foreground"
          )}
        >
          <CloudUpload className="size-6" />
        </div>
        <div>
          <p className="text-sm font-medium text-foreground">
            {value ? "Replace document" : "Drag & drop your receipt"}
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            PNG, JPEG, WebP or PDF · up to 10 MB
          </p>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".png,.jpg,.jpeg,.webp,.pdf,image/png,image/jpeg,image/webp,application/pdf"
          className="hidden"
          onChange={(event) => acceptFile(event.target.files?.[0])}
        />
      </div>

      {value && (
        <div className="flex items-center gap-3 rounded-lg border border-border bg-card px-3 py-2.5">
          <div className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
            {isImage ? <FileImage className="size-5" /> : <FileText className="size-5" />}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-foreground">{value.name}</p>
            <p className="text-xs text-muted-foreground">
              {(value.size / 1024).toFixed(1)} KB ·{" "}
              {value.type === "application/pdf" ? "PDF" : value.type.split("/")[1].toUpperCase()}
            </p>
          </div>
          <button
            type="button"
            aria-label="Remove file"
            onClick={() => onChange(null)}
            className="flex size-7 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
          >
            <X className="size-4" />
          </button>
        </div>
      )}

      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}