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
  category_confidence: number | null;
  category_manually_set: boolean;
  category_source: string;
  categorization_reason: string | null;
  categorization_rule: string | null;
  payment_type: string | null;
  is_recurring_candidate: boolean;
  created_at: string;
  updated_at: string;
};

export type TransactionFilters = {
  date_from?: string;
  date_to?: string;
  category?: string;
  merchant?: string;
  search?: string;
  payment_type?: string;
  min_amount?: string;
  max_amount?: string;
  limit?: number;
  offset?: number;
};

export type TransactionListResponse = {
  transactions: Transaction[];
  limit: number;
  offset: number;
  count: number;
};

export type CategorySummaryItem = {
  category: string;
  total_amount: string;
  transaction_count: number;
  percentage_of_total_expenses: string;
};

export type CategorySummaryResponse = {
  items: CategorySummaryItem[];
  total_expenses: string;
  total_income: string;
  transaction_count: number;
};

export type MerchantSummaryItem = {
  merchant_normalized: string;
  total_amount: string;
  transaction_count: number;
  first_seen: string;
  last_seen: string;
};

export type MerchantSummaryResponse = {
  items: MerchantSummaryItem[];
};

export type Subscription = {
  id: string;
  merchant_name: string;
  average_amount: string;
  frequency: string;
  first_seen: string;
  last_seen: string;
  next_expected_date: string | null;
  confidence_score: number;
  status: string;
  created_at: string;
  updated_at: string;
};

export type SubscriptionFilters = {
  status?: string;
  frequency?: string;
  search?: string;
  limit?: number;
  offset?: number;
};

export type SubscriptionListResponse = {
  subscriptions: Subscription[];
  limit: number;
  offset: number;
  count: number;
};

export type SubscriptionDetectionResponse = {
  subscriptions: Subscription[];
  detected_count: number;
  updated_count: number;
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

function queryString(params?: Record<string, string | number | undefined>): string {
  const query = new URLSearchParams();
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      query.set(key, String(value));
    }
  });
  const serialized = query.toString();
  return serialized ? `?${serialized}` : "";
}

export function listTransactions(token: string, filters?: TransactionFilters): Promise<TransactionListResponse> {
  return request<TransactionListResponse>(
    `/transactions${queryString(filters)}`,
    {
      method: "GET",
      headers: authHeaders(token),
    },
    "Could not load transactions.",
  );
}

export function getTransaction(token: string, transactionId: string): Promise<Transaction> {
  return request<Transaction>(
    `/transactions/${transactionId}`,
    {
      method: "GET",
      headers: authHeaders(token),
    },
    "Could not load that transaction.",
  );
}

export function updateTransactionCategory(
  token: string,
  transactionId: string,
  category: string,
): Promise<Transaction> {
  return request<Transaction>(
    `/transactions/${transactionId}/category`,
    {
      method: "PATCH",
      headers: authHeaders(token),
      body: JSON.stringify({ category }),
    },
    "Could not update the category.",
  );
}

export function getCategorySummary(
  token: string,
  filters?: Pick<TransactionFilters, "date_from" | "date_to">,
): Promise<CategorySummaryResponse> {
  return request<CategorySummaryResponse>(
    `/transactions/categories/summary${queryString(filters)}`,
    {
      method: "GET",
      headers: authHeaders(token),
    },
    "Could not load category summary.",
  );
}

export function getMerchantSummary(
  token: string,
  filters?: Pick<TransactionFilters, "date_from" | "date_to" | "category">,
): Promise<MerchantSummaryResponse> {
  return request<MerchantSummaryResponse>(
    `/transactions/merchants/summary${queryString(filters)}`,
    {
      method: "GET",
      headers: authHeaders(token),
    },
    "Could not load merchant summary.",
  );
}

export function listSubscriptions(
  token: string,
  filters?: SubscriptionFilters,
): Promise<SubscriptionListResponse> {
  return request<SubscriptionListResponse>(
    `/subscriptions${queryString(filters)}`,
    {
      method: "GET",
      headers: authHeaders(token),
    },
    "Could not load recurring payments.",
  );
}

export function detectSubscriptions(token: string): Promise<SubscriptionDetectionResponse> {
  return request<SubscriptionDetectionResponse>(
    "/subscriptions/detect",
    {
      method: "POST",
      headers: authHeaders(token),
    },
    "Could not detect recurring payments.",
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
