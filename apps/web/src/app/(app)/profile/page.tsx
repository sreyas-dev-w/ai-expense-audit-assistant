"use client"

import { BriefcaseIcon, BuildingIcon, ShieldCheckIcon, UserIcon } from "@/components/icons"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { useSession } from "@/hooks/use-session"
import { formatMoney } from "@/lib/format"

function initials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase()
}

function Row({ icon: Icon, label, value }: { icon: typeof UserIcon; label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 py-3">
      <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
        <Icon className="size-4" />
      </div>
      <div className="flex min-w-0 flex-1 items-center justify-between gap-2">
        <span className="text-sm text-muted-foreground">{label}</span>
        <span className="text-sm font-medium">{value}</span>
      </div>
    </div>
  )
}

export default function ProfilePage() {
  const employee = useSession((state) => state.employee)
  const details = useSession((state) => state.details)

  if (!employee) return null

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <div className="flex items-center gap-4">
        <Avatar className="size-14">
          <AvatarFallback className="text-lg">{initials(employee.employee_name)}</AvatarFallback>
        </Avatar>
        <div>
          <h1 className="font-heading text-xl font-semibold">{employee.employee_name}</h1>
          <p className="text-sm text-muted-foreground">{employee.employee_id}</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Employment details</CardTitle>
        </CardHeader>
        <CardContent className="divide-y p-0 px-(--card-spacing)">
          <Row icon={UserIcon} label="Job level" value={employee.job_level} />
          <Row
            icon={ShieldCheckIcon}
            label="Role"
            value={employee.is_manager ? "Manager" : "Employee"}
          />
          <Row icon={UserIcon} label="Manager" value={employee.manager_id ?? "None"} />
          <Row icon={UserIcon} label="Username" value={employee.username ?? "-"} />
        </CardContent>
      </Card>

      {details?.project && (
        <Card>
          <CardHeader>
            <CardTitle>Project</CardTitle>
          </CardHeader>
          <CardContent className="divide-y p-0 px-(--card-spacing)">
            <Row icon={BriefcaseIcon} label="Project" value={details.project.project_name} />
            <Row icon={BriefcaseIcon} label="Project code" value={details.project.project_code} />
            <Row
              icon={UserIcon}
              label="Project lead"
              value={details.project.project_lead_id ?? "-"}
            />
          </CardContent>
        </Card>
      )}

      {details?.account && (
        <Card>
          <CardHeader>
            <CardTitle>Account</CardTitle>
          </CardHeader>
          <CardContent className="divide-y p-0 px-(--card-spacing)">
            <Row icon={BuildingIcon} label="Account" value={details.account.account_name} />
            <Row icon={BuildingIcon} label="Fiscal year" value={details.account.fiscal_year} />
            <Row
              icon={BuildingIcon}
              label="Budget allocated"
              value={formatMoney(details.account.budget_allocated, details.account.currency)}
            />
            <Row
              icon={BuildingIcon}
              label="Remaining budget"
              value={formatMoney(details.account.remaining_budget, details.account.currency)}
            />
          </CardContent>
        </Card>
      )}
    </div>
  )
}
