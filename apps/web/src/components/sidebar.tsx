"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  FilePlus2,
  Files,
  ShieldCheck,
  ChevronsUpDown,
  CircleUserRound,
  Building2,
  UserRoundCog,
  ScanSearch,
} from "lucide-react";
import { cn } from "cn";
import { useUser } from "@/hooks/use-user";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { AppNavigationItem } from "@/lib/types";

function initials(name: string): string {
  return name
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

export function Sidebar() {
  const { user, users, isManager, setActiveEmployeeId } = useUser();
  const pathname = usePathname();

  const managers = users.filter((u) => u.is_manager);
  const contributors = users.filter((u) => !u.is_manager);

  const navItems: AppNavigationItem[] = [
    {
      label: "Create New Claim",
      href: "/claims/new",
      description: "Submit a claim for automated audit",
      visible: true,
    },
    {
      label: "My Claims",
      href: "/claims",
      description: "Track submitted and historical claims",
      visible: true,
    },
    {
      label: "Team Approvals",
      href: "/approvals",
      description: "Under-review claims from direct reports",
      visible: isManager,
    },
  ];

  const visibleItems = navItems.filter((item) => item.visible);

  const isActive = (href: string) =>
    href === "/claims"
      ? pathname === "/claims"
      : pathname.startsWith(href);

  return (
    <aside className="sticky top-0 flex h-screen w-72 shrink-0 flex-col border-r border-sidebar-border bg-sidebar">
      <div className="flex h-16 items-center gap-2.5 border-b border-sidebar-border px-5">
        <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10">
          <ScanSearch className="size-5 text-primary" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold leading-tight text-sidebar-foreground">
            expense<span className="text-primary">.audit</span>
          </p>
          <p className="text-[11px] leading-tight text-muted-foreground">
            AI verification pipeline
          </p>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-4">
        <p className="px-2 pb-2 text-[11px] font-medium tracking-wider text-muted-foreground">
          WORKSPACE
        </p>
        <nav className="flex flex-col gap-1">
          {visibleItems.map((item) => {
            const active = isActive(item.href);
            const Icon =
              item.href === "/claims/new"
                ? FilePlus2
                : item.href === "/claims"
                  ? Files
                  : ShieldCheck;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "group relative flex items-center gap-3 rounded-lg px-2.5 py-2 text-sm transition-colors",
                  active
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-foreground"
                )}
              >
                <span
                  className={cn(
                    "absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-primary transition-opacity",
                    active ? "opacity-100" : "opacity-0"
                  )}
                />
                <Icon
                  className={cn(
                    "size-4 shrink-0",
                    active ? "text-primary" : "text-muted-foreground group-hover:text-sidebar-foreground"
                  )}
                />
                <span className="flex-1">{item.label}</span>
                {item.label === "Team Approvals" && <Badge variant="secondary">Mgr</Badge>}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="border-t border-sidebar-border p-3">
        <DropdownMenu>
          <DropdownMenuTrigger
            asChild
            className="cursor-pointer outline-none"
          >
            <button
              type="button"
              data-slot="sidebar-user-switcher"
              className={cn(
                "flex w-full items-center gap-3 rounded-lg border border-sidebar-border bg-sidebar-accent/40 p-2.5 text-left transition-colors hover:bg-sidebar-accent/70"
              )}
            >
              {user ? (
                <>
                  <Avatar name={user.employee_name} />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-sidebar-foreground">
                      {user.employee_name}
                    </span>
                    <span className="block truncate text-[11px] text-muted-foreground">
                      {user.employee_id} · {user.job_level}
                    </span>
                  </span>
                  <ChevronsUpDown className="size-4 shrink-0 text-muted-foreground" />
                </>
              ) : (
                <div className="flex w-full items-center gap-3">
                  <Skeleton className="size-9 rounded-full" />
                  <span className="flex-1">
                    <Skeleton className="h-3 w-24" />
                    <Skeleton className="mt-1 h-2.5 w-16" />
                  </span>
                </div>
              )}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-(--radix-dropdown-menu-trigger-width)">
            <div className="px-1.5 pt-1 pb-1">
              <p className="text-xs font-medium text-foreground">
                Mock active user
              </p>
              <p className="text-[11px] text-muted-foreground">
                Switch profiles to test layout changes
              </p>
            </div>
            <DropdownMenuSeparator />
            <DropdownMenuGroup>
              <DropdownMenuLabel>Managers</DropdownMenuLabel>
              {managers.slice(0, 8).map((employee) => (
                <DropdownUserItem
                  key={employee.employee_id}
                  employee={employee}
                  active={user?.employee_id === employee.employee_id}
                  onSelect={() => setActiveEmployeeId(employee.employee_id)}
                />
              ))}
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuGroup>
              <DropdownMenuLabel>Contributors</DropdownMenuLabel>
              {contributors.slice(0, 12).map((employee) => (
                <DropdownUserItem
                  key={employee.employee_id}
                  employee={employee}
                  active={user?.employee_id === employee.employee_id}
                  onSelect={() => setActiveEmployeeId(employee.employee_id)}
                />
              ))}
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>

        <div className="mt-2 flex items-center gap-2 px-1">
          {isManager ? (
            <Badge className="bg-primary/15 text-primary">
              <UserRoundCog className="size-3" /> Manager access
            </Badge>
          ) : (
            <Badge variant="secondary">
              <CircleUserRound className="size-3" /> Contributor
            </Badge>
          )}
          <Badge variant="outline" className="gap-1">
            <Building2 className="size-3" />
            {user?.project_code ?? "—"}
          </Badge>
        </div>
      </div>
    </aside>
  );
}

function Avatar({ name }: { name: string }) {
  return (
    <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary/15 text-xs font-semibold text-primary ring-1 ring-primary/30">
      {initials(name)}
    </span>
  );
}

function DropdownUserItem({
  employee,
  active,
  onSelect,
}: {
  employee: { employee_id: string; employee_name: string; job_level: string };
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <DropdownMenuItem
      className="gap-2 text-sm"
      onSelect={(event) => {
        event.preventDefault();
        onSelect();
      }}
    >
      <Avatar name={employee.employee_name} />
      <span className="min-w-0 flex-1">
        <span className="block truncate font-medium text-foreground">
          {employee.employee_name}
        </span>
        <span className="block truncate text-[11px] text-muted-foreground">
          {employee.employee_id} · {employee.job_level}
        </span>
      </span>
      {active && <span className="size-1.5 shrink-0 rounded-full bg-primary" />}
    </DropdownMenuItem>
  );
}