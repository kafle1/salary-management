import type { Metadata } from "next";
import "./globals.css";
import { NavLink } from "@/components/nav-link";

export const metadata: Metadata = {
  title: "Salary Management",
  description: "Payroll spend across countries and currencies for a 10,000 person org",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <header className="masthead">
            <div className="wordmark">
              ACME <span>salary management</span>
            </div>
            <nav>
              <NavLink href="/">Dashboard</NavLink>
              <NavLink href="/employees">Employees</NavLink>
            </nav>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
