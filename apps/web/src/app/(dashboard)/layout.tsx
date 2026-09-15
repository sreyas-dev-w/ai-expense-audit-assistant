import { Providers } from "@/components/providers";
import { Sidebar } from "@/components/sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Providers>
      <div className="relative flex min-h-dvh">
        <Sidebar />
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </Providers>
  );
}