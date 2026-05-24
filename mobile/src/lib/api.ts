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

export type SpendingAnomaly = {
  id: string;
  anomaly_type: string;
  category: string | null;
  merchant_name: string | null;
  amount_delta: string | null;
  percentage_change: number | null;
  explanation: string;
  severity: string;
  period_start: string | null;
  period_end: string | null;
  baseline_period_start: string | null;
  baseline_period_end: string | null;
  transaction_count: number | null;
  created_at: string;
};

export type AnomalyFilters = {
  month?: string;
  severity?: string;
  anomaly_type?: string;
  limit?: number;
  offset?: number;
};

export type AnomalyListResponse = {
  anomalies: SpendingAnomaly[];
  limit: number;
  offset: number;
  count: number;
};

export type AnomalyDetectionResponse = {
  anomalies: SpendingAnomaly[];
  detected_count: number;
  month: string;
};

export type AnomalySummaryResponse = {
  total_anomalies: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  top_categories: Array<{ name: string; count: number }>;
  top_merchants: Array<{ name: string; count: number }>;
  month: string;
};

export type DashboardTopCategory = {
  category: string;
  total_amount: string;
  transaction_count: number;
  percentage_of_total_expenses: string;
};

export type DashboardRecentTransaction = {
  id: string;
  transaction_date: string;
  merchant_normalized: string | null;
  amount: string;
  currency: string;
  category: string | null;
  category_confidence: number | null;
};

export type DashboardSubscriptionItem = {
  id: string;
  merchant_name: string;
  average_amount: string;
  frequency: string;
  next_expected_date: string | null;
  status: string;
};

export type DashboardAnomalyItem = {
  id: string;
  anomaly_type: string;
  category: string | null;
  merchant_name: string | null;
  amount_delta: string | null;
  percentage_change: number | null;
  explanation: string;
  severity: string;
  created_at: string;
};

export type DashboardSummaryResponse = {
  month: string | null;
  currency: string;
  total_income: string;
  total_expenses: string;
  net_flow: string;
  transaction_count: number;
  top_categories: DashboardTopCategory[];
  recent_transactions: DashboardRecentTransaction[];
  subscription_summary: {
    active_count: number;
    estimated_monthly_total: string;
    upcoming_items: DashboardSubscriptionItem[];
  };
  anomaly_summary: {
    total_count: number;
    high_count: number;
    medium_count: number;
    low_count: number;
    latest_items: DashboardAnomalyItem[];
  };
  needs_review_count: number;
  latest_upload: {
    id: string;
    file_name: string;
    upload_status: string;
    total_rows: number;
    processed_rows: number;
    created_at: string;
  } | null;
  has_data: boolean;
};

export type MonthlyReportTopCategory = {
  category: string;
  total_amount: string;
  transaction_count: number;
  percentage_of_total_expenses: string;
};

export type MonthlyReportSubscription = {
  merchant_name: string;
  average_amount: string;
  frequency: string;
  next_expected_date: string | null;
  confidence_score: number;
};

export type MonthlyReportAnomaly = {
  anomaly_type: string;
  severity: string;
  explanation: string;
  amount_delta: string | null;
  percentage_change: number | null;
};

export type MonthlyInsightReport = {
  id: string;
  user_id: string;
  month: string;
  currency: string;
  total_income: string;
  total_expenses: string;
  total_spend: string;
  net_flow: string;
  transaction_count: number;
  top_categories: MonthlyReportTopCategory[];
  detected_subscriptions: MonthlyReportSubscription[];
  anomalies: MonthlyReportAnomaly[];
  needs_review_count: number;
  largest_merchant_total: {
    merchant_name: string;
    total_amount: string;
    transaction_count: number;
  } | null;
  recurring_payment_count: number;
  ai_summary: string;
  generated_status: string;
  generation_source: string;
  safety_flags: string[];
  has_data: boolean;
  created_at: string;
  updated_at: string | null;
};

export type MonthlyReportListResponse = {
  reports: MonthlyInsightReport[];
  limit: number;
  offset: number;
  count: number;
};

export type MonthlyReportFilters = {
  month?: string;
  limit?: number;
  offset?: number;
};

export type ImportResult = {
  upload_id: string;
  total_rows: number;
  processed_rows: number;
  duplicate_rows: number;
  invalid_rows: Array<{ row_number: number; reason: string }>;
};

export type DemoScenario = "basic" | "subscriptions" | "budget_leaks" | "needs_review" | "full_portfolio";

export type DemoScenarioInfo = {
  key: DemoScenario;
  title: string;
  description: string;
};

export type DemoLoadResult = ImportResult & {
  scenario: DemoScenario;
  transactions_created: number;
  uploads_created: number;
  subscriptions_detected: number;
  anomalies_detected: number;
  reports_generated: number;
  reset_existing_demo: boolean;
  run_processing: boolean;
  message: string;
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

export type ChatTransactionDraft = {
  transaction_type: "expense" | "income";
  transaction_date: string;
  merchant: string;
  description: string;
  amount: string;
  currency: string;
  category: string;
  payment_type: string;
  confidence: number;
  source: "ai_chat_manual";
};

export type ChatExpenseParseResponse = {
  reply: string;
  clarification_needed: boolean;
  clarification_question: string | null;
  draft: ChatTransactionDraft | null;
};

export type ChatExpenseConfirmResponse = {
  message: string;
  transaction: Transaction;
};

export type PrivacySummary = {
  user_email: string;
  transaction_count: number;
  upload_count: number;
  subscription_count: number;
  anomaly_count: number;
  monthly_report_count: number;
  has_demo_data: boolean;
  latest_upload_date: string | null;
  latest_report_date: string | null;
  data_sources_used: {
    csv_upload: boolean;
    manual_entry: boolean;
    paste_import: boolean;
    demo_data: boolean;
  };
  privacy_notes: string[];
};

export type DeletedCounts = {
  transactions: number;
  uploads: number;
  subscriptions: number;
  anomalies: number;
  monthly_reports: number;
  audit_logs: number;
  user: number;
};

export type DataExport = {
  metadata: {
    exported_at: string;
    app: "Tally";
    scope: "current_user";
    notice: string;
  };
  user: {
    id: string;
    email: string;
    created_at: string;
  };
  uploads: unknown[];
  transactions: unknown[];
  subscriptions: unknown[];
  anomalies: unknown[];
  monthly_reports: unknown[];
};

export type ClearDemoDataResponse = {
  message: string;
  deleted_counts: DeletedCounts;
};

export type DeleteAppDataResponse = {
  message: string;
  deleted_counts: DeletedCounts;
};

export type DeleteAccountResponse = {
  message: string;
  deleted_counts: DeletedCounts;
  session_notice: string;
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

export function detectAnomalies(token: string, month?: string): Promise<AnomalyDetectionResponse> {
  return request<AnomalyDetectionResponse>(
    "/anomalies/detect",
    {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ month }),
    },
    "Could not run budget leak detection.",
  );
}

export function getAnomalies(token: string, filters?: AnomalyFilters): Promise<AnomalyListResponse> {
  return request<AnomalyListResponse>(
    `/anomalies${queryString(filters)}`,
    {
      method: "GET",
      headers: authHeaders(token),
    },
    "Could not load budget leaks.",
  );
}

export function getAnomalySummary(token: string, month?: string): Promise<AnomalySummaryResponse> {
  return request<AnomalySummaryResponse>(
    `/anomalies/summary${queryString({ month })}`,
    {
      method: "GET",
      headers: authHeaders(token),
    },
    "Could not load budget leak summary.",
  );
}

export function getDashboardSummary(token: string, month?: string): Promise<DashboardSummaryResponse> {
  return request<DashboardSummaryResponse>(
    `/dashboard/summary${queryString({ month })}`,
    {
      method: "GET",
      headers: authHeaders(token),
    },
    "Could not load dashboard.",
  );
}

export function generateMonthlyReport(
  token: string,
  month: string,
  useAi = true,
  forceRefresh = false,
): Promise<MonthlyInsightReport> {
  return request<MonthlyInsightReport>(
    "/reports/monthly/generate",
    {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ month, use_ai: useAi, force_refresh: forceRefresh }),
    },
    "Could not generate the monthly report.",
  );
}

export function getMonthlyReports(
  token: string,
  filters?: MonthlyReportFilters,
): Promise<MonthlyReportListResponse> {
  return request<MonthlyReportListResponse>(
    `/reports/monthly${queryString(filters)}`,
    {
      method: "GET",
      headers: authHeaders(token),
    },
    "Could not load monthly reports.",
  );
}

export function getMonthlyReportById(token: string, reportId: string): Promise<MonthlyInsightReport> {
  return request<MonthlyInsightReport>(
    `/reports/monthly/${reportId}`,
    {
      method: "GET",
      headers: authHeaders(token),
    },
    "Could not load that monthly report.",
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

export function parseChatExpense(
  token: string,
  message: string,
  timezone = "Asia/Manila",
): Promise<ChatExpenseParseResponse> {
  return request<ChatExpenseParseResponse>(
    "/ai/expense/parse",
    {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ message, timezone }),
    },
    "I couldn't understand that transaction yet.",
  );
}

export function confirmChatExpense(
  token: string,
  draft: ChatTransactionDraft,
): Promise<ChatExpenseConfirmResponse> {
  return request<ChatExpenseConfirmResponse>(
    "/ai/expense/confirm",
    {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ draft }),
    },
    "We couldn't save this transaction. Please try again.",
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

export function getDemoScenarios(token: string): Promise<{ scenarios: DemoScenarioInfo[] }> {
  return request<{ scenarios: DemoScenarioInfo[] }>(
    "/demo/scenarios",
    {
      method: "GET",
      headers: authHeaders(token),
    },
    "Could not load demo scenarios.",
  );
}

export function loadDemoData(
  token: string,
  scenario: DemoScenario = "full_portfolio",
  resetExistingDemo = false,
  runProcessing = true,
): Promise<DemoLoadResult> {
  return request<DemoLoadResult>(
    "/demo/load-sample-data",
    {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({
        scenario,
        reset_existing_demo: resetExistingDemo,
        run_processing: runProcessing,
      }),
    },
    "Could not load demo data.",
  );
}

export function resetDemoData(
  token: string,
  scenario: DemoScenario = "full_portfolio",
  runProcessing = true,
): Promise<DemoLoadResult> {
  return request<DemoLoadResult>(
    "/demo/reset",
    {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ scenario, run_processing: runProcessing }),
    },
    "Could not reset demo data.",
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

export function getPrivacySummary(token: string): Promise<PrivacySummary> {
  return request<PrivacySummary>(
    "/settings/privacy/summary",
    {
      method: "GET",
      headers: authHeaders(token),
    },
    "We couldn't load your privacy summary. Please try again.",
  );
}

export function exportUserData(token: string): Promise<DataExport> {
  return request<DataExport>(
    "/settings/privacy/export",
    {
      method: "GET",
      headers: authHeaders(token),
    },
    "We couldn't export your data. Please try again.",
  );
}

export function clearDemoData(token: string): Promise<ClearDemoDataResponse> {
  return request<ClearDemoDataResponse>(
    "/settings/privacy/clear-demo-data",
    {
      method: "POST",
      headers: authHeaders(token),
    },
    "We couldn't clear demo data. Please try again.",
  );
}

export function deleteAppData(token: string, confirmation: string): Promise<DeleteAppDataResponse> {
  return request<DeleteAppDataResponse>(
    "/settings/privacy/delete-app-data",
    {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ confirmation }),
    },
    "We couldn't delete your data. Please try again.",
  );
}

export function deleteAccount(token: string, confirmation: string): Promise<DeleteAccountResponse> {
  return request<DeleteAccountResponse>(
    "/settings/privacy/delete-account",
    {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify({ confirmation }),
    },
    "We couldn't delete your account. Please try again.",
  );
}
