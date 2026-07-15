// Typed client for the DocVerify backend. JWT is stored in localStorage and
// attached to every request.

export type FieldType = "string" | "integer" | "number" | "boolean" | "date";

export interface SchemaField {
  name: string;
  type: FieldType;
  description: string;
  required: boolean;
}

export interface DocType {
  key: string;
  label: string;
  fields: SchemaField[];
}

export interface FieldResult {
  field: string;
  extracted: unknown;
  expected: unknown;
  status: "match" | "mismatch" | "missing" | "no_reference";
}

export interface VerificationResult {
  id?: string;
  doc_type: string;
  filename: string;
  document_type_detected?: string | null;
  doc_type_mismatch: boolean;
  extracted: Record<string, unknown>;
  field_results: FieldResult[];
  overall_status: "matched" | "mismatched" | "extracted";
  engine?: string | null;
  created_at?: string | null;
}

export interface UserInfo {
  username: string;
  email: string;
  role: string;
}

export type Provider = "offline" | "gemini" | "groq" | "openrouter" | "openai" | "anthropic";

export interface LLMSettings {
  provider: Provider;
  model: string;
  base_url: string;
  api_key_set: boolean;
}

const TOKEN_KEY = "docverify_token";

export const token = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const t = token.get();
  if (t) headers.set("Authorization", `Bearer ${t}`);
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(path, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  register: (username: string, email: string, password: string) =>
    request<{ access_token: string }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, email, password }),
    }),

  login: (username: string, password: string) =>
    request<{ access_token: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  me: () => request<UserInfo>("/api/auth/me"),

  changePassword: (current_password: string, new_password: string) =>
    request<void>("/api/auth/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password, new_password }),
    }),

  getSettings: () => request<LLMSettings>("/api/settings"),

  updateSettings: (s: {
    provider: string;
    model: string;
    base_url: string;
    api_key?: string;
  }) =>
    request<LLMSettings>("/api/settings", { method: "PUT", body: JSON.stringify(s) }),

  listDocTypes: () => request<DocType[]>("/api/doc-types"),

  createDocType: (dt: DocType) =>
    request<DocType>("/api/doc-types", { method: "POST", body: JSON.stringify(dt) }),

  updateDocType: (dt: DocType) =>
    request<DocType>(`/api/doc-types/${dt.key}`, { method: "PUT", body: JSON.stringify(dt) }),

  verify: (docType: string, file: File, reference?: Record<string, unknown>) => {
    const form = new FormData();
    form.append("doc_type", docType);
    form.append("file", file);
    if (reference && Object.keys(reference).length) {
      form.append("reference", JSON.stringify(reference));
    }
    return request<VerificationResult>("/api/verify", { method: "POST", body: form });
  },

  listVerifications: () => request<VerificationResult[]>("/api/verifications"),
};
