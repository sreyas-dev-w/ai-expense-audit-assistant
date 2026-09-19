"use client"

import * as React from "react"
import { toast } from "sonner"
import { ApiError } from "@/lib/api/client"
import {
  Loader2Icon,
  ShieldCheckIcon,
  Trash2Icon,
  UploadIcon,
} from "@/components/icons"
import { FilePreview } from "@/components/file-preview"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { useSession } from "@/hooks/use-session"
import {
  useDeletePolicyDocument,
  usePolicyDocuments,
  useUploadPolicyDocument,
} from "@/hooks/use-policies"
import { formatDateTime } from "@/lib/format"
import type { PolicyDocumentSummary } from "@/lib/types/api"

function statusVariant(status: string): "default" | "secondary" | "destructive" {
  if (status === "completed") return "default"
  if (status === "failed") return "destructive"
  return "secondary"
}

export default function PolicyPage() {
  const employee = useSession((state) => state.employee)
  const { data, isLoading } = usePolicyDocuments()
  const upload = useUploadPolicyDocument()
  const deleteDoc = useDeletePolicyDocument()

  const [file, setFile] = React.useState<File | null>(null)
  const [fileError, setFileError] = React.useState<string | null>(null)
  const [pendingDeleteId, setPendingDeleteId] = React.useState<number | null>(null)

  async function handleUpload() {
    if (!file) {
      setFileError("Choose a policy PDF to upload.")
      return
    }
    setFileError(null)
    try {
      const result = await upload.mutateAsync(file)
      toast.success(`Policy "${result.filename}" ingested`, {
        description: `${result.chunk_count} chunks embedded into the policy store.`,
      })
      setFile(null)
    } catch (err) {
      toast.error("Could not upload policy", {
        description: err instanceof ApiError ? err.message : "Please try again.",
      })
    }
  }

  async function handleDelete(doc: PolicyDocumentSummary) {
    setPendingDeleteId(doc.policy_id)
    try {
      await deleteDoc.mutateAsync(doc.policy_id)
      toast.success(`Policy "${doc.filename}" deleted`)
    } catch (err) {
      toast.error("Could not delete policy", {
        description: err instanceof ApiError ? err.message : "Please try again.",
      })
    } finally {
      setPendingDeleteId(null)
    }
  }

  if (employee?.job_level !== "L6") {
    return (
      <div className="mx-auto flex max-w-md flex-col items-center gap-4 py-16 text-center">
        <div className="flex size-12 items-center justify-center rounded-xl bg-muted text-muted-foreground">
          <ShieldCheckIcon className="size-6" />
        </div>
        <h1 className="font-heading text-xl font-semibold">Not authorized</h1>
        <p className="text-sm text-muted-foreground">
          Policy management is restricted to L6 users. Contact your administrator
          if you believe this is a mistake.
        </p>
      </div>
    )
  }

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <div>
        <h1 className="font-heading text-xl font-semibold">Policy documents</h1>
        <p className="text-sm text-muted-foreground">
          Upload and manage the expense policy PDFs used to audit claims.
          Restricted to L6 users.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Upload policy</CardTitle>
          <CardDescription>Upload a policy PDF to chunk and embed into the policy store.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div>
            <label
              htmlFor="policy-file"
              className="flex cursor-pointer items-center gap-3 rounded-lg border border-dashed border-input px-3 py-3 text-sm hover:bg-muted/50"
            >
              <UploadIcon className="size-4 text-muted-foreground" />
              <span className="text-muted-foreground">
                {file ? file.name : "Choose a PDF to upload"}
              </span>
            </label>
            <input
              id="policy-file"
              type="file"
              accept="application/pdf"
              className="sr-only"
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null)
                setFileError(null)
              }}
            />
            {fileError && <p className="mt-1 text-sm text-destructive">{fileError}</p>}
          </div>
          <FilePreview file={file} label="Policy" />
          <div className="flex justify-end">
            <Button
              type="button"
              onClick={handleUpload}
              disabled={upload.isPending || !file}
            >
              {upload.isPending ? <Loader2Icon className="animate-spin" /> : <UploadIcon />}
              Upload policy
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Ingested documents</CardTitle>
          <CardDescription>Policy PDFs currently available to the policy store.</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex flex-col gap-3">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Filename</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Chunks</TableHead>
                  <TableHead>Uploaded</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(data ?? []).length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
                      No policy documents yet. Upload one above.
                    </TableCell>
                  </TableRow>
                ) : (
                  (data ?? []).map((doc) => (
                    <TableRow key={doc.policy_id}>
                      <TableCell className="font-medium">{doc.filename}</TableCell>
                      <TableCell>
                        <Badge variant={statusVariant(doc.status)}>{doc.status}</Badge>
                      </TableCell>
                      <TableCell className="tabular-nums">{doc.chunk_count}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDateTime(doc.created_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button
                              size="icon-sm"
                              variant="ghost"
                              aria-label={`Delete ${doc.filename}`}
                              disabled={deleteDoc.isPending}
                            >
                              {pendingDeleteId === doc.policy_id ? (
                                <Loader2Icon className="animate-spin" />
                              ) : (
                                <Trash2Icon />
                              )}
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent size="sm">
                            <AlertDialogHeader>
                              <AlertDialogMedia>
                                <Trash2Icon />
                              </AlertDialogMedia>
                              <AlertDialogTitle>Delete policy?</AlertDialogTitle>
                              <AlertDialogDescription>
                                “{doc.filename}” and its {doc.chunk_count} chunks will be removed
                                from the policy store. This cannot be undone.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancel</AlertDialogCancel>
                              <AlertDialogAction onClick={() => handleDelete(doc)}>
                                Delete
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}