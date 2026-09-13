"use client";

import { MoreHorizontalIcon, PencilIcon, PlusIcon, Trash2Icon } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, startTransition, use, useActionState, useEffect, useState, useTransition } from "react";
import { toast } from "sonner";
import { deleteEmployee, saveEmployee, type FormState } from "@/app/actions";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import type { Employee, FilterOptions, PayableCountry } from "@/lib/api";

type Editor = {
  openCreate: () => void;
  openEdit: (employee: Employee) => void;
  confirmDelete: (employee: Employee) => void;
};

const EditorContext = createContext<Editor | null>(null);

function useEditor(): Editor {
  const editor = use(EditorContext);
  if (!editor) throw new Error("wrap the page in <EmployeeEditor>");
  return editor;
}

type Props = {
  countries: PayableCountry[];
  options: FilterOptions;
  children: React.ReactNode;
};

/** One sheet and one confirm dialog per page, opened from any row or button below it. */
export function EmployeeEditor({ countries, options, children }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  // a fresh key per open remounts the form, so last attempt's errors and typing are gone
  const [form, setForm] = useState<{ key: number; employee: Employee | null } | null>(null);
  const [deleting, setDeleting] = useState<Employee | null>(null);
  const [lastDeleting, setLastDeleting] = useState<Employee | null>(null);
  const [pending, startDelete] = useTransition();

  const editor: Editor = {
    openCreate: () => setForm({ key: Date.now(), employee: null }),
    openEdit: (employee) => setForm({ key: Date.now(), employee }),
    confirmDelete: (employee) => {
      setDeleting(employee);
      setLastDeleting(employee);
    },
  };

  const onSaved = (saved: Employee, created: boolean) => {
    setForm(null);
    toast.success(created ? `Added ${saved.full_name}` : `Saved ${saved.full_name}`);
    if (created) router.push(`/employees/${saved.id}`);
  };

  const onDelete = (employee: Employee) =>
    startDelete(async () => {
      const result = await deleteEmployee(employee.id);
      if (!result.ok) {
        toast.error(result.message ?? "Couldn't delete this person.");
        return;
      }
      setDeleting(null);
      toast.success(`Deleted ${employee.full_name}`);
      if (pathname === `/employees/${employee.id}`) router.push("/employees");
      else router.refresh();
    });

  // the dialog animates out after close, so keep showing who it was about until then
  const shown = deleting ?? lastDeleting;

  return (
    <EditorContext value={editor}>
      {children}

      <Sheet open={form !== null} onOpenChange={(open) => (open ? null : setForm(null))}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-md">
          {form ? (
            <EmployeeForm
              key={form.key}
              employee={form.employee}
              countries={countries}
              options={options}
              onCancel={() => setForm(null)}
              onSaved={onSaved}
            />
          ) : null}
        </SheetContent>
      </Sheet>

      <AlertDialog
        open={deleting !== null}
        onOpenChange={(open) => (open || pending ? null : setDeleting(null))}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete {shown?.full_name}?</AlertDialogTitle>
            <AlertDialogDescription>
              Their record and salary history go too. This can&apos;t be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={pending}>Keep</AlertDialogCancel>
            <Button
              variant="destructive"
              disabled={pending || !deleting}
              onClick={() => deleting && onDelete(deleting)}
            >
              {pending ? "Deleting..." : "Delete"}
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </EditorContext>
  );
}

function Field({
  name,
  label,
  error,
  hint,
  children,
}: {
  name: string;
  label: string;
  error?: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={name}>{label}</Label>
      {children}
      {error ? (
        <p id={`${name}-error`} className="text-xs text-destructive">
          {error}
        </p>
      ) : hint ? (
        <p className="text-xs text-muted-foreground">{hint}</p>
      ) : null}
    </div>
  );
}

const INITIAL: FormState = { ok: false };

function today(): string {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

function EmployeeForm({
  employee,
  countries,
  options,
  onCancel,
  onSaved,
}: {
  employee: Employee | null;
  countries: PayableCountry[];
  options: FilterOptions;
  onCancel: () => void;
  onSaved: (employee: Employee, created: boolean) => void;
}) {
  const [state, formAction, saving] = useActionState(saveEmployee, INITIAL);
  const [country, setCountry] = useState<string | null>(employee?.country_code ?? null);
  const currency = countries.find((c) => c.code === country)?.currency;
  const errors = state.errors ?? {};
  const general = !state.ok && state.message && Object.keys(errors).length === 0 ? state.message : null;

  useEffect(() => {
    if (state.ok && state.employee) onSaved(state.employee, employee === null);
    // onSaved changes identity every render; the state change is the only trigger that matters
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state]);

  const invalid = (field: string) =>
    errors[field] ? { "aria-invalid": true, "aria-describedby": `${field}-error` } : {};

  return (
    <form
      className="flex h-full flex-col"
      noValidate
      onSubmit={(event) => {
        // submitting through a transition keeps React from resetting the inputs on a failed save
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        startTransition(() => formAction(data));
      }}
    >
      <SheetHeader>
        <SheetTitle>{employee ? `Edit ${employee.full_name}` : "Add an employee"}</SheetTitle>
        <SheetDescription>
          {employee
            ? "A change to pay is added to their salary history."
            : "Their starting salary becomes the first line of their salary history."}
        </SheetDescription>
      </SheetHeader>

      <input type="hidden" name="id" value={employee?.id ?? ""} />

      <div className="grid gap-4 px-4">
        {general ? (
          <p role="alert" className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {general}
          </p>
        ) : null}

        <Field name="full_name" label="Full name" error={errors.full_name}>
          <Input
            id="full_name"
            name="full_name"
            defaultValue={employee?.full_name}
            autoComplete="off"
            required
            {...invalid("full_name")}
          />
        </Field>

        <Field name="email" label="Work email" error={errors.email}>
          <Input
            id="email"
            name="email"
            type="email"
            defaultValue={employee?.email}
            autoComplete="off"
            required
            {...invalid("email")}
          />
        </Field>

        <Field name="country_code" label="Country" error={errors.country_code}>
          <Select
            name="country_code"
            items={countries.map((c) => ({ value: c.code, label: c.name }))}
            value={country}
            onValueChange={setCountry}
          >
            <SelectTrigger id="country_code" className="w-full" {...invalid("country_code")}>
              <SelectValue placeholder="Pick a country" />
            </SelectTrigger>
            <SelectContent>
              {countries.map((c) => (
                <SelectItem key={c.code} value={c.code}>
                  {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field name="department" label="Department" error={errors.department}>
            <Input
              id="department"
              name="department"
              list="department-options"
              defaultValue={employee?.department}
              autoComplete="off"
              required
              {...invalid("department")}
            />
            <datalist id="department-options">
              {options.departments.map((d) => (
                <option key={d} value={d} />
              ))}
            </datalist>
          </Field>

          <Field name="role" label="Role" error={errors.role}>
            <Input
              id="role"
              name="role"
              list="role-options"
              defaultValue={employee?.role}
              autoComplete="off"
              required
              {...invalid("role")}
            />
            <datalist id="role-options">
              {options.roles.map((r) => (
                <option key={r} value={r} />
              ))}
            </datalist>
          </Field>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field name="hire_date" label="Hire date" error={errors.hire_date}>
            <Input
              id="hire_date"
              name="hire_date"
              type="date"
              max={today()}
              defaultValue={employee?.hire_date}
              required
              {...invalid("hire_date")}
            />
          </Field>

          <Field
            name="salary_amount"
            label="Yearly salary"
            error={errors.salary_amount}
            hint={currency ? `Paid in ${currency}` : "Pick a country to see the currency"}
          >
            <div className="relative">
              <Input
                id="salary_amount"
                name="salary_amount"
                type="number"
                inputMode="decimal"
                min="0.01"
                step="0.01"
                defaultValue={employee?.salary.amount}
                required
                className={currency ? "pr-12" : undefined}
                {...invalid("salary_amount")}
              />
              {currency ? (
                <span className="pointer-events-none absolute top-1/2 right-2.5 -translate-y-1/2 text-xs text-muted-foreground">
                  {currency}
                </span>
              ) : null}
            </div>
          </Field>
        </div>

        <Field
          name="salary_note"
          label={employee ? "Reason for a pay change" : "Note"}
          error={errors.salary_note}
          hint="Optional. Shows next to this salary in the history."
        >
          <Input
            id="salary_note"
            name="salary_note"
            placeholder={employee ? "Annual review, promotion..." : "Offer letter, band..."}
            autoComplete="off"
            {...invalid("salary_note")}
          />
        </Field>
      </div>

      <SheetFooter className="mt-auto flex-row justify-end">
        <Button type="button" variant="outline" onClick={onCancel} disabled={saving}>
          Cancel
        </Button>
        <Button type="submit" disabled={saving}>
          {saving ? "Saving..." : employee ? "Save changes" : "Add employee"}
        </Button>
      </SheetFooter>
    </form>
  );
}

export function AddEmployeeButton() {
  const { openCreate } = useEditor();
  return (
    <Button onClick={openCreate}>
      <PlusIcon />
      Add employee
    </Button>
  );
}

export function EmployeeRowMenu({ employee }: { employee: Employee }) {
  const { openEdit, confirmDelete } = useEditor();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={<Button variant="ghost" size="icon-sm" aria-label={`Actions for ${employee.full_name}`} />}
      >
        <MoreHorizontalIcon />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem render={<Link href={`/employees/${employee.id}`} />}>View</DropdownMenuItem>
        <DropdownMenuItem onClick={() => openEdit(employee)}>
          <PencilIcon />
          Edit
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem variant="destructive" onClick={() => confirmDelete(employee)}>
          <Trash2Icon />
          Delete
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function EmployeeActions({ employee }: { employee: Employee }) {
  const { openEdit, confirmDelete } = useEditor();
  return (
    <div className="flex gap-2">
      <Button variant="outline" onClick={() => openEdit(employee)}>
        <PencilIcon />
        Edit
      </Button>
      <Button variant="outline" onClick={() => confirmDelete(employee)}>
        <Trash2Icon />
        Delete
      </Button>
    </div>
  );
}
