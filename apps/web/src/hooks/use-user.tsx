"use client";

import * as React from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Employee } from "@/lib/types";

type UserContextValue = {
  user: Employee | null;
  users: Employee[];
  isLoading: boolean;
  isManager: boolean;
  setActiveEmployeeId: (employeeId: string) => void;
  refresh: () => void;
  error: string | null;
};

const UserContext = React.createContext<UserContextValue | null>(null);

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [activeEmployeeId, setActiveEmployeeId] = React.useState<string>("EMP-002");
  const queryClient = useQueryClient();

  const { data: users = [], isLoading: usersLoading } = useQuery({
    queryKey: ["employees"],
    queryFn: api.getEmployees,
    staleTime: 5 * 60 * 1000,
  });

  const { data: user, isLoading: userLoading } = useQuery({
    queryKey: ["employee", activeEmployeeId],
    queryFn: () => api.getEmployee(activeEmployeeId),
    enabled: !!activeEmployeeId,
    staleTime: 5 * 60 * 1000,
  });

  const value = React.useMemo<UserContextValue>(
    () => ({
      user: user ?? null,
      users,
      isLoading: usersLoading || userLoading,
      isManager: user?.is_manager ?? false,
      setActiveEmployeeId,
      refresh: () => {
        queryClient.invalidateQueries({ queryKey: ["claims"] });
        queryClient.invalidateQueries({ queryKey: ["approvals"] });
        queryClient.invalidateQueries({ queryKey: ["employee"] });
      },
      error: null,
    }),
    [user, users, usersLoading, userLoading, queryClient]
  );

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}

export function useUser(): UserContextValue {
  const ctx = React.useContext(UserContext);
  if (!ctx) {
    throw new Error("useUser must be used within a UserProvider");
  }
  return ctx;
}