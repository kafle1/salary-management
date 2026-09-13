"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

export function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  const pathname = usePathname();
  // /employees/42 still counts as being in Employees
  const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={cn(
        "rounded-md px-2 py-1.5 text-muted-foreground sm:px-2.5 transition-colors hover:text-foreground",
        active && "bg-muted font-medium text-foreground",
      )}
    >
      {children}
    </Link>
  );
}
