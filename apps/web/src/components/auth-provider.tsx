"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useRouter } from "next/navigation";

import { api, TOKEN_STORAGE_KEY } from "@/lib/api";
import type { EmployeeProfile } from "@/lib/types";

interface AuthState {
  profile: EmployeeProfile | null;
  /** True until the stored token has been checked against the backend. */
  loading: boolean;
  signIn: (email: string, password: string) => Promise<EmployeeProfile>;
  signOut: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [profile, setProfile] = useState<EmployeeProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = window.localStorage.getItem(TOKEN_STORAGE_KEY);
    if (!token) {
      setLoading(false);
      return;
    }
    let active = true;
    api
      .me()
      .then((me) => {
        if (active) setProfile(me);
      })
      .catch(() => {
        window.localStorage.removeItem(TOKEN_STORAGE_KEY);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const result = await api.login(email, password);
    window.localStorage.setItem(TOKEN_STORAGE_KEY, result.access_token);
    setProfile(result.profile);
    return result.profile;
  }, []);

  const signOut = useCallback(() => {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    setProfile(null);
    router.replace("/login");
  }, [router]);

  const value = useMemo(
    () => ({ profile, loading, signIn, signOut }),
    [profile, loading, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
