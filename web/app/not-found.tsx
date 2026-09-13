import Link from "next/link";
import { PageHeader } from "@/components/page";
import { buttonVariants } from "@/components/ui/button";

export default function NotFound() {
  return (
    <>
      <PageHeader title="Not found" description="That person or page doesn't exist. They may have been deleted." />
      <Link href="/employees" className={buttonVariants({ variant: "outline" })}>
        Back to employees
      </Link>
    </>
  );
}
