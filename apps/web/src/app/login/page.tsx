"use client"

import * as React from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { z } from "zod"
import { ClipboardCheckIcon, Loader2Icon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { FormField } from "@/components/form-field"
import { login } from "@/lib/api/auth"
import { getAllEmployees, getEmployeeDetails } from "@/lib/api/employees"
import { useSession } from "@/hooks/use-session"
import { ApiError } from "@/lib/api/client"

const loginSchema = z.object({
  username: z.string().min(1, "Enter your employee username"),
  password: z.string().min(1, "Enter your password"),
})

type LoginValues = z.infer<typeof loginSchema>

export default function LoginPage() {
  const router = useRouter()
  const setSession = useSession((state) => state.setSession)
  const [serverError, setServerError] = React.useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = React.useState(false)

  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: "", password: "" },
  })

  async function onSubmit(values: LoginValues) {
    setServerError(null)
    setIsSubmitting(true)
    try {
      const result = await login(values)

      if (!result.authenticated || !result.employee_id) {
        setServerError("Incorrect username or password.")
        return
      }

      const [employees, details] = await Promise.all([
        getAllEmployees(),
        getEmployeeDetails(result.employee_id),
      ])

      const employee = employees.find((e) => e.employee_id === result.employee_id)
      if (!employee) {
        setServerError("Signed in, but your employee record could not be found.")
        return
      }

      setSession(employee, details)
      router.push("/claims")
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-[100dvh] items-center justify-center bg-muted/30 p-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="flex flex-col items-center gap-2 text-center">
          <div className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <ClipboardCheckIcon className="size-5" />
          </div>
          <h1 className="font-heading text-lg font-semibold">AI Expense Audit Assistant</h1>
          <p className="text-sm text-muted-foreground">Sign in to review and submit expense claims.</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Sign in</CardTitle>
            <CardDescription>Use your employee username and password.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
              <FormField
                label="Username"
                htmlFor="username"
                error={form.formState.errors.username?.message}
              >
                <Input
                  id="username"
                  autoComplete="username"
                  placeholder="emp001"
                  aria-invalid={!!form.formState.errors.username}
                  {...form.register("username")}
                />
              </FormField>

              <FormField
                label="Password"
                htmlFor="password"
                error={form.formState.errors.password?.message}
              >
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  aria-invalid={!!form.formState.errors.password}
                  {...form.register("password")}
                />
              </FormField>

              {serverError && (
                <Alert variant="destructive">
                  <AlertDescription>{serverError}</AlertDescription>
                </Alert>
              )}

              <Button type="submit" disabled={isSubmitting} className="mt-1 w-full">
                {isSubmitting && <Loader2Icon className="animate-spin" />}
                Sign in
              </Button>
            </form>
          </CardContent>
        </Card>

        <p className="text-center text-xs text-muted-foreground">
          Demo accounts: <span className="font-mono">emp001</span> through{" "}
          <span className="font-mono">emp032</span>, password{" "}
          <span className="font-mono">password@123</span>.{" "}
          <Link href="/" className="underline underline-offset-4 hover:text-foreground">
            Back to overview
          </Link>
        </p>
      </div>
    </div>
  )
}
