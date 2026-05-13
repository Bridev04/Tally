import { API_BASE_URL } from "@/config";
import type { TokenResponse, User } from "@/types/auth";

type AuthPayload = {
  email: string;
  password: string;
};

type ApiErrorPayload = {
  detail?: unknown;
};

export type Transaction = {
  id: string;
  transaction_date: string;
  merchant_raw: string;
  merchant_normalized: string | null;
  description: string | null;
  amount: string;
  currency: string;
  category: string | null;
  created_at: string;
};

export type ImportResult = {
  upload_id: string;
  total_rows: number;
  processed_rows: number;
  duplicate_rows: number;
  invalid_rows: Array<{ row_number: number; reason: string }>;
};

export type PastePreview = {
  valid_rows: Array<{
    row_number: number;
    transaction_date: string;
    merchant: string;
    merchant_normalized: string;
    description: string;
    amount: string;
    currency: string;
  }>;
  invalid_rows: Array<{ row_number: number; reason: string }>;
};

export type ManualTransactionPayload = {
  transaction_date: string;
  merchant: string;
  description: string;
  amount: string;
  currency: string;
  category?: string;
};

const fallbackMessage = "Something went wrong. Please try again.";

function safeErrorMessage(payload: ApiErrorPayload, fallback = fallbackMessage): string {
  if (typeof payload.detail === "string") {
    return payload.detail;
  }
  return fallback;
}

async function request<T>(
  path: string,
  options: RequestInit,
  fallback: string = fallbackMessage,
): Promise<T> {
  const hasFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(hasFormData ? {} : { "content-type": "application/json" }),
      ...options.headers,
    },
  });

  const payload = (await response.json().catch(() => ({}))) as ApiErrorPayload;

  if (!response.ok) {
    throw new Error(safeErrorMessage(payload, fallback));
  }

  return payload as T;
}

export function register(payload: AuthPayload): Promise<TokenResponse> {
  return request<TokenResponse>(
    "/auth/register",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    "Could not create your account.",
  );
}

export function login(payload: AuthPayload): Promise<TokenResponse> {
  return request<TokenResponse>(
    "/auth/login",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    "Could not sign you in.",
  );
}

export function getMe(token: string): Promise<User> {
  return request<User>(
    "/auth/me",
    {
      method: "GET",
      headers: {
        authorization: `Bearer ${token}`,
      },
    },
    "Your session expired. Please sign in again.",
  );
}

function authHeaders(token: string) {
  return {
    authorization: `Bearer ${token}`,
  };
}

export function listTransactions(token: string): Promise<{ transactions: Transaction[] }> {
  return request<{ transactions: Transaction[] }>(
    "/transactions",
    {
      method: "GET",
      headers: authHeaders(token),
    },
    "Could not load transactions.",
  );
}

export function createManualTransaction(
  token: string,
  payload: ManualTransactionPayload,
): Promise<{ transaction: Transaction }> {
  return request<{ transaction: Transaction }>(
    "/transactions/manual",
    {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(payload),
    },
    "Could not save the transaction.",
  );
}

export function previewPasteImport(token: string, text: string): Promise<PastePreview> {
  return request<PastePreview>(
    "/imports/paste/preview",
    {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ text }),
    },
    "Could not preview those transactions.",
  );
}

export function confirmPasteImport(token: string, text: string): Promise<ImportResult> {
  return request<ImportResult>(
    "/imports/paste/confirm",
    {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ text }),
    },
    "Could not import those transactions.",
  );
}

export function loadDemoData(token: string): Promise<ImportResult> {
  return request<ImportResult>(
    "/demo/load-sample-data",
    {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ allow_overwrite: false }),
    },
    "Could not load demo data.",
  );
}

export async function uploadCsv(token: string, formData: FormData): Promise<ImportResult> {
  return request<ImportResult>(
    "/uploads/csv",
    {
      method: "POST",
      headers: authHeaders(token),
      body: formData,
    },
    "Could not upload the CSV file.",
  );
}
