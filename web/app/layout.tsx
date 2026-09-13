import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";
import { NavLink } from "@/components/nav-link";
import { Toaster } from "@/components/ui/sonner";
import { cn } from "@/lib/utils";

const geist = Geist({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "Salary Management",
  description: "Pay across countries and currencies for a 10,000 person org",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={cn("font-sans", geist.variable)}>
      <body className="min-h-screen antialiased">
        <header className="border-b bg-background/80 backdrop-blur">
          <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-4 whitespace-nowrap sm:gap-6 sm:px-6">
            <span className="font-semibold tracking-tight">
              ACME <span className="hidden font-normal text-muted-foreground sm:inline">Salaries</span>
            </span>
            <nav className="flex items-center gap-0.5 text-sm sm:gap-1">
              <NavLink href="/">Dashboard</NavLink>
              <NavLink href="/employees">Employees</NavLink>
              <NavLink href="/pay-review">Pay review</NavLink>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 sm:py-8">{children}</main>
        <Toaster position="bottom-right" />
      </body>
    </html>
  );
}
