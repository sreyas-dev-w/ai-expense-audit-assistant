"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  CheckCheckIcon,
  FilePlus2Icon,
  FilesIcon,
  LogOutIcon,
  ReceiptTextIcon,
} from "lucide-react";

import { useAuth } from "@/components/auth-provider";
import { Badge } from "@/components/ui/badge";
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
} from "@/components/ui/sidebar";

const NAV_ITEMS = [
  { href: "/claims/new", label: "Create Claim", icon: FilePlus2Icon },
  { href: "/claims", label: "View Claims", icon: FilesIcon },
  {
    href: "/approvals",
    label: "Approve Claims",
    icon: CheckCheckIcon,
    managerOnly: true,
  },
] as const;

export function AppSidebar() {
  const pathname = usePathname();
  const { profile, signOut } = useAuth();

  const items = NAV_ITEMS.filter(
    (item) => !("managerOnly" in item) || profile?.is_manager,
  );

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <div className="flex items-center gap-2 px-2 py-1.5">
          <div className="bg-sidebar-accent flex size-7 shrink-0 items-center justify-center rounded-md">
            <ReceiptTextIcon className="size-4" />
          </div>
          <div className="grid flex-1 text-left text-sm leading-tight group-data-[collapsible=icon]:hidden">
            <span className="truncate font-medium">Expense Audit</span>
            <span className="text-muted-foreground truncate text-xs">
              Assistant
            </span>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Claims</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => {
                // `/claims/new` must not also light up `/claims`.
                const active =
                  item.href === "/claims"
                    ? pathname === "/claims" ||
                      /^\/claims\/\d+$/.test(pathname)
                    : pathname.startsWith(item.href);
                return (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton
                      asChild
                      isActive={active}
                      tooltip={item.label}
                    >
                      <Link href={item.href}>
                        <item.icon />
                        <span>{item.label}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <div className="grid gap-2 px-2 py-1.5 group-data-[collapsible=icon]:hidden">
          <div className="grid text-sm leading-tight">
            <span className="truncate font-medium">
              {profile?.employee_name}
            </span>
            <span className="text-muted-foreground truncate text-xs">
              {profile?.email}
            </span>
          </div>
          <div className="flex flex-wrap gap-1">
            <Badge variant="secondary">{profile?.job_level}</Badge>
            {profile?.is_manager ? <Badge>Manager</Badge> : null}
          </div>
        </div>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton onClick={signOut} tooltip="Sign out">
              <LogOutIcon />
              <span>Sign out</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
