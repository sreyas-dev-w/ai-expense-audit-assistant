"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import {
  ClipboardCheckIcon,
  FileTextIcon,
  LogOutIcon,
  PlusCircleIcon,
  ScaleIcon,
  UserIcon,
} from "@/components/icons"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { ThemeToggle } from "@/components/theme-toggle"
import { useSession } from "@/hooks/use-session"

function initials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase()
}

export function AppSidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const employee = useSession((state) => state.employee)
  const clearSession = useSession((state) => state.clearSession)

  const isManager = employee?.is_manager ?? false

  const items = [
    { href: "/claims/new", label: "New Claim", icon: PlusCircleIcon },
    { href: "/claims", label: "My Claims", icon: FileTextIcon },
    ...(isManager
      ? [{ href: "/approvals", label: "Approvals", icon: ScaleIcon }]
      : []),
    { href: "/profile", label: "Profile", icon: UserIcon },
  ]

  function handleLogout() {
    clearSession()
    router.push("/login")
  }

  return (
    <Sidebar variant="inset" collapsible="icon">
      <SidebarHeader>
        <div className="flex items-center gap-2 px-2 py-1.5">
          <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <ClipboardCheckIcon className="size-4" />
          </div>
          <span className="truncate font-heading text-sm font-semibold">
            Expense Audit
          </span>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Workspace</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => {
                const isActive =
                  pathname === item.href || pathname.startsWith(`${item.href}/`)
                return (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton asChild isActive={isActive} tooltip={item.label}>
                      <Link href={item.href}>
                        <item.icon />
                        <span>{item.label}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <div className="flex items-center justify-between gap-2 px-1 py-1">
          <div className="flex min-w-0 items-center gap-2">
            <Avatar className="size-7">
              <AvatarFallback className="text-xs">
                {employee ? initials(employee.employee_name) : "?"}
              </AvatarFallback>
            </Avatar>
            <div className="flex min-w-0 flex-col leading-tight">
              <span className="truncate text-sm font-medium">
                {employee?.employee_name ?? "Loading…"}
              </span>
              <span className="truncate text-xs text-muted-foreground">
                {employee?.employee_id}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-0.5">
            <ThemeToggle />
            <SidebarMenuButton
              onClick={handleLogout}
              aria-label="Log out"
              className="size-8 shrink-0 justify-center p-0"
            >
              <LogOutIcon />
            </SidebarMenuButton>
          </div>
        </div>
      </SidebarFooter>
    </Sidebar>
  )
}
