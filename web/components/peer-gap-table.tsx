import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { PeerGap } from "@/lib/api";
import { money } from "@/lib/format";

export function PeerGapTable({ items }: { items: PeerGap[] }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="pl-4">Person</TableHead>
          <TableHead>Role and country</TableHead>
          <TableHead className="text-right">Paid (USD)</TableHead>
          <TableHead className="text-right">Peer median</TableHead>
          <TableHead className="text-right">Of median</TableHead>
          <TableHead className="pr-4 text-right">Gap</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {items.map(({ employee, peer_median, peers, percent_of_median }) => {
          const gap = Number(peer_median.amount) - Number(employee.salary_in_base.amount);
          return (
            <TableRow key={employee.id}>
              <TableCell className="pl-4">
                <Link href={`/employees/${employee.id}`} className="font-medium hover:underline">
                  {employee.full_name}
                </Link>
                <div className="text-xs text-muted-foreground">{employee.department}</div>
              </TableCell>
              <TableCell>
                {employee.role}
                <div className="text-xs text-muted-foreground">
                  {employee.country_name}, {peers} peers
                </div>
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {money(employee.salary_in_base.amount, employee.salary_in_base.currency)}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {money(peer_median.amount, peer_median.currency)}
              </TableCell>
              <TableCell className="text-right">
                <Badge variant={percent_of_median < 65 ? "destructive" : "secondary"}>
                  {percent_of_median}%
                </Badge>
              </TableCell>
              <TableCell className="pr-4 text-right text-muted-foreground tabular-nums">
                {money(String(gap), peer_median.currency)}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
