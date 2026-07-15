// Parse a JSON or Excel file into a flat { fieldName: value } map used to
// auto-fill the reference-values form on the Verify page.
//
// Supported shapes:
//   JSON  — an object: { "name": "Asha", "roll_number": "42" }
//   Excel — either
//            (a) headers in row 1, values in row 2 (one record across columns), or
//            (b) a two-column key/value sheet (field name | value), one field per row.

import * as XLSX from "xlsx";

const toStr = (v: unknown): string =>
  v === null || v === undefined ? "" : String(v);

function fromJson(text: string): Record<string, string> {
  const data = JSON.parse(text);
  if (typeof data !== "object" || data === null || Array.isArray(data)) {
    throw new Error("JSON must be a single object of field: value pairs");
  }
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(data)) out[k] = toStr(v);
  return out;
}

function fromExcel(buf: ArrayBuffer): Record<string, string> {
  const wb = XLSX.read(buf, { type: "array" });
  const sheet = wb.Sheets[wb.SheetNames[0]];
  if (!sheet) throw new Error("The spreadsheet has no sheets");

  const rows = XLSX.utils.sheet_to_json<unknown[]>(sheet, { header: 1, blankrows: false });
  if (rows.length === 0) throw new Error("The spreadsheet is empty");

  const out: Record<string, string> = {};

  // Two-column key/value layout (field | value), when no row is wider than 2.
  const maxWidth = Math.max(...rows.map((r) => r.length));
  if (maxWidth <= 2 && rows.length > 1) {
    for (const row of rows) {
      const key = toStr(row[0]).trim();
      if (key) out[key] = toStr(row[1]);
    }
    return out;
  }

  // Headers in row 1, values in row 2.
  const headers = rows[0].map(toStr);
  const values = rows[1] ?? [];
  headers.forEach((h, i) => {
    const key = h.trim();
    if (key) out[key] = toStr(values[i]);
  });
  return out;
}

export async function parseReferenceFile(file: File): Promise<Record<string, string>> {
  const name = file.name.toLowerCase();
  if (name.endsWith(".json")) {
    return fromJson(await file.text());
  }
  if (name.endsWith(".xlsx") || name.endsWith(".xls") || name.endsWith(".csv")) {
    return fromExcel(await file.arrayBuffer());
  }
  throw new Error("Unsupported file — upload a .json, .xlsx, .xls or .csv file");
}
