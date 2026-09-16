"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/auth-provider";
import { Skeleton } from "@/components/ui/skeleton";

export default function Home() {
  const router = useRouter();
  const { profile, loading } = useAuth();

  useEffect(() => {
    if (loading) return;
    router.replace(profile ? "/claims" : "/login");
  }, [loading, profile, router]);

  return (
    <div className="flex flex-1 items-center justify-center p-8">
      <Skeleton className="h-8 w-48" />
    </div>
  );
}
