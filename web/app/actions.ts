"use server";

import { revalidatePath } from "next/cache";
import { sendJson, type Employee } from "@/lib/api";

export type FormState = {
  ok: boolean;
  message?: string;
  errors?: Record<string, string>;
  employee?: Employee;
};

const FIELDS = [
  "full_name",
  "email",
  "country_code",
  "department",
  "role",
  "hire_date",
  "salary_amount",
  "salary_note",
] as const;

const UNREACHABLE = "Couldn't reach the API. Check it is running and try again.";

export async function saveEmployee(_: FormState, form: FormData): Promise<FormState> {
  const body = Object.fromEntries(FIELDS.map((field) => [field, String(form.get(field) ?? "")]));
  const id = Number(form.get("id"));

  try {
    const result = id
      ? await sendJson<Employee>("PUT", `/employees/${id}`, body)
      : await sendJson<Employee>("POST", "/employees", body);
    if (!result.ok) return { ok: false, message: result.detail, errors: result.errors };
    revalidatePath("/", "layout");
    return { ok: true, employee: result.data };
  } catch {
    return { ok: false, message: UNREACHABLE };
  }
}

export async function deleteEmployee(id: number): Promise<FormState> {
  try {
    const result = await sendJson<null>("DELETE", `/employees/${id}`);
    // someone else already deleted them, which is the outcome that was asked for
    if (!result.ok && result.status !== 404) return { ok: false, message: result.detail };
    // no revalidate here: re-rendering a deleted person's page would flash a 404 before the redirect
    return { ok: true };
  } catch {
    return { ok: false, message: UNREACHABLE };
  }
}
