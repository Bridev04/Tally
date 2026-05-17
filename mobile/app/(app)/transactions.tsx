import { Ionicons } from "@expo/vector-icons";
import { router, useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useAuth } from "@/context/AuthContext";
import {
  CategorySummaryResponse,
  getCategorySummary,
  getTransaction,
  listTransactions,
  loadDemoData,
  Transaction,
  TransactionFilters,
  updateTransactionCategory,
} from "@/lib/api";
import { colors, radius, typography } from "@/theme";

const categories = [
  "food",
  "transportation",
  "rent",
  "subscriptions",
  "shopping",
  "entertainment",
  "utilities",
  "education",
  "health",
  "income",
  "transfer",
  "fees",
  "other",
  "needs_review",
];

const categoryLabels: Record<string, string> = {
  food: "Food",
  transportation: "Transportation",
  rent: "Rent",
  subscriptions: "Subscriptions",
  shopping: "Shopping",
  entertainment: "Entertainment",
  utilities: "Utilities",
  education: "Education",
  health: "Health",
  income: "Income",
  transfer: "Transfer",
  fees: "Fees",
  other: "Other",
  needs_review: "Needs review",
};

type AmountMode = "all" | "expense" | "income";

export default function TransactionsScreen() {
  const { token } = useAuth();
  const params = useLocalSearchParams<{ category?: string }>();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [summary, setSummary] = useState<CategorySummaryResponse | null>(null);
  const [search, setSearch] = useState("");
  const [merchant, setMerchant] = useState("");
  const [category, setCategory] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [amountMode, setAmountMode] = useState<AmountMode>("all");
  const [isLoading, setIsLoading] = useState(false);
  const [isDemoLoading, setIsDemoLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);
  const [draftCategory, setDraftCategory] = useState("");
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [isSavingCategory, setIsSavingCategory] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    if (typeof params.category === "string" && categories.includes(params.category)) {
      setCategory(params.category);
    }
  }, [params.category]);

  const filters = useMemo<TransactionFilters>(() => {
    const nextFilters: TransactionFilters = {
      limit: 50,
      search: search.trim() || undefined,
      merchant: merchant.trim() || undefined,
      category: category || undefined,
      date_from: dateFrom.trim() || undefined,
      date_to: dateTo.trim() || undefined,
    };
    if (amountMode === "expense") {
      nextFilters.max_amount = "-0.01";
    }
    if (amountMode === "income") {
      nextFilters.min_amount = "0.01";
    }
    return nextFilters;
  }, [amountMode, category, dateFrom, dateTo, merchant, search]);

  const loadData = useCallback(async () => {
    if (!token) {
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const [transactionResponse, categorySummary] = await Promise.all([
        listTransactions(token, filters),
        getCategorySummary(token, {
          date_from: filters.date_from,
          date_to: filters.date_to,
        }),
      ]);
      setTransactions(transactionResponse.transactions);
      setSummary(categorySummary);
    } catch {
      setError("We could not load transactions. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, [filters, token]);

  useEffect(() => {
    const handle = setTimeout(() => {
      loadData();
    }, 250);
    return () => clearTimeout(handle);
  }, [loadData]);

  const hasActiveFilters =
    Boolean(search.trim()) ||
    Boolean(merchant.trim()) ||
    Boolean(category) ||
    Boolean(dateFrom.trim()) ||
    Boolean(dateTo.trim()) ||
    amountMode !== "all";
  const summaryCurrency = transactions[0]?.currency ?? "PHP";
  const needsReviewCount = summary?.items.find((item) => item.category === "needs_review")?.transaction_count ?? 0;

  async function openTransaction(transaction: Transaction) {
    if (!token) {
      return;
    }
    setSelectedTransaction(transaction);
    setDraftCategory(transaction.category ?? "needs_review");
    setDetailError(null);
    setSaveMessage(null);
    setIsDetailLoading(true);
    try {
      const freshTransaction = await getTransaction(token, transaction.id);
      setSelectedTransaction(freshTransaction);
      setDraftCategory(freshTransaction.category ?? "needs_review");
    } catch {
      setDetailError("We could not load the latest details.");
    } finally {
      setIsDetailLoading(false);
    }
  }

  async function saveCategory() {
    if (!token || !selectedTransaction || isSavingCategory) {
      return;
    }
    setIsSavingCategory(true);
    setDetailError(null);
    setSaveMessage(null);
    try {
      const updated = await updateTransactionCategory(token, selectedTransaction.id, draftCategory);
      setSelectedTransaction(updated);
      setTransactions((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setSaveMessage("Category updated.");
      const categorySummary = await getCategorySummary(token, {
        date_from: filters.date_from,
        date_to: filters.date_to,
      });
      setSummary(categorySummary);
    } catch {
      setDetailError("We could not update the category. Please try again.");
      setDraftCategory(selectedTransaction.category ?? "needs_review");
    } finally {
      setIsSavingCategory(false);
    }
  }

  async function handleDemoData() {
    if (!token || isDemoLoading) {
      return;
    }
    setIsDemoLoading(true);
    setError(null);
    try {
      await loadDemoData(token);
      await loadData();
    } catch {
      setError("We could not load demo data. Please try again.");
    } finally {
      setIsDemoLoading(false);
    }
  }

  const topCategories = summary?.items.slice(0, 3) ?? [];

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.content}>
        <View style={styles.headerRow}>
          <View>
            <Text style={styles.title}>Transactions</Text>
            <Text style={styles.subtitle}>{summary?.transaction_count ?? transactions.length} transactions</Text>
          </View>
          {isLoading ? <ActivityIndicator color={colors.primary} /> : null}
        </View>

        <View style={styles.summaryRow}>
          <SummaryCard label="Expenses" value={formatAmount(summary?.total_expenses ?? "0.00", summaryCurrency)} />
          <SummaryCard label="Count" value={String(summary?.transaction_count ?? 0)} />
          <SummaryCard label="Needs Review" value={String(needsReviewCount)} />
        </View>

        {topCategories.length > 0 ? (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.categorySummaryRow}>
            {topCategories.map((item) => (
              <View key={item.category} style={styles.categorySummary}>
                <Text style={styles.categorySummaryLabel}>{labelForCategory(item.category)}</Text>
                <Text style={styles.categorySummaryAmount}>{formatAmount(item.total_amount, summaryCurrency)}</Text>
                <Text style={styles.categorySummaryMeta}>{item.percentage_of_total_expenses}%</Text>
              </View>
            ))}
          </ScrollView>
        ) : null}

        <View style={styles.filters}>
          <View style={styles.searchBox}>
            <Ionicons color={colors.textMuted} name="search" size={18} />
            <TextInput
              autoCapitalize="none"
              onChangeText={setSearch}
              placeholder="Search merchant or description"
              placeholderTextColor={colors.textMuted}
              style={styles.searchInput}
              value={search}
            />
          </View>

          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
            <FilterChip isSelected={!category} label="All" onPress={() => setCategory("")} />
            <FilterChip
              isSelected={category === "needs_review"}
              label="Needs Review"
              onPress={() => setCategory("needs_review")}
            />
            {categories.map((item) => (
              item === "needs_review" ? null : (
              <FilterChip
                key={item}
                isSelected={category === item}
                label={labelForCategory(item)}
                onPress={() => setCategory(item)}
              />
              )
            ))}
          </ScrollView>

          <View style={styles.segmented}>
            <SegmentButton isSelected={amountMode === "all"} label="All" onPress={() => setAmountMode("all")} />
            <SegmentButton
              isSelected={amountMode === "expense"}
              label="Expenses"
              onPress={() => setAmountMode("expense")}
            />
            <SegmentButton isSelected={amountMode === "income"} label="Income" onPress={() => setAmountMode("income")} />
          </View>

          <View style={styles.filterGrid}>
            <TextInput
              autoCapitalize="none"
              onChangeText={setMerchant}
              placeholder="Merchant"
              placeholderTextColor={colors.textMuted}
              style={styles.filterInput}
              value={merchant}
            />
            <TextInput
              autoCapitalize="none"
              onChangeText={setDateFrom}
              placeholder="From YYYY-MM-DD"
              placeholderTextColor={colors.textMuted}
              style={styles.filterInput}
              value={dateFrom}
            />
            <TextInput
              autoCapitalize="none"
              onChangeText={setDateTo}
              placeholder="To YYYY-MM-DD"
              placeholderTextColor={colors.textMuted}
              style={styles.filterInput}
              value={dateTo}
            />
          </View>
        </View>

        {error ? <Text style={styles.error}>{error}</Text> : null}

        {!isLoading && transactions.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons color={colors.primary} name="receipt-outline" size={28} />
            <Text style={styles.emptyTitle}>
              {hasActiveFilters
                ? "No matching transactions."
                : "No transactions yet. Import transactions to see your spending patterns."}
            </Text>
            {!hasActiveFilters ? (
              <View style={styles.emptyActions}>
                <ActionButton
                  icon="add-circle-outline"
                  label="Import transactions"
                  onPress={() => router.push("/(app)/import")}
                />
                <ActionButton
                  icon="sparkles-outline"
                  isLoading={isDemoLoading}
                  label="Try demo data"
                  onPress={handleDemoData}
                />
              </View>
            ) : null}
          </View>
        ) : (
          <View style={styles.list}>
            {transactions.map((item) => (
              <TransactionRow key={item.id} item={item} onPress={() => openTransaction(item)} />
            ))}
          </View>
        )}
      </ScrollView>

      <Modal
        animationType="slide"
        onRequestClose={() => setSelectedTransaction(null)}
        transparent
        visible={selectedTransaction !== null}
      >
        <View style={styles.modalBackdrop}>
          <View style={styles.sheet}>
            {selectedTransaction ? (
              <ScrollView contentContainerStyle={styles.sheetContent}>
                <View style={styles.sheetHeader}>
                  <View style={styles.sheetTitleBlock}>
                    <Text style={styles.sheetMerchant}>{selectedTransaction.merchant_raw}</Text>
                    <Text style={styles.sheetDate}>{selectedTransaction.transaction_date}</Text>
                  </View>
                  <Pressable
                    accessibilityRole="button"
                    onPress={() => setSelectedTransaction(null)}
                    style={styles.iconButton}
                  >
                    <Ionicons color={colors.text} name="close" size={22} />
                  </Pressable>
                </View>

                {isDetailLoading ? <ActivityIndicator color={colors.primary} /> : null}
                {detailError ? <Text style={styles.error}>{detailError}</Text> : null}
                {saveMessage ? <Text style={styles.message}>{saveMessage}</Text> : null}

                <Text style={[styles.detailAmount, selectedTransaction.amount.startsWith("-") ? styles.expense : styles.income]}>
                  {formatSignedAmount(selectedTransaction.amount, selectedTransaction.currency)}
                </Text>

                <DetailRow label="Description" value={selectedTransaction.description ?? "Not provided"} />
                <DetailRow label="Currency" value={selectedTransaction.currency} />
                <DetailRow label="Payment" value={selectedTransaction.payment_type ?? "Not provided"} />
                <DetailRow
                  label="Confidence"
                  value={confidenceLabel(selectedTransaction)}
                />
                <DetailRow label="Source" value={sourceLabel(selectedTransaction.category_source)} />
                {selectedTransaction.categorization_reason ? (
                  <DetailRow label="Reason" value={selectedTransaction.categorization_reason} />
                ) : null}

                <View style={styles.pickerBlock}>
                  <Text style={styles.sectionLabel}>Category</Text>
                  <View style={styles.categoryPicker}>
                    {categories.map((item) => (
                      <FilterChip
                        key={item}
                        isSelected={draftCategory === item}
                        label={labelForCategory(item)}
                        onPress={() => setDraftCategory(item)}
                      />
                    ))}
                  </View>
                </View>

                <Pressable
                  accessibilityRole="button"
                  disabled={isSavingCategory || draftCategory === (selectedTransaction.category ?? "needs_review")}
                  onPress={saveCategory}
                  style={({ pressed }) => [
                    styles.saveButton,
                    (pressed || isSavingCategory) && styles.pressed,
                    draftCategory === (selectedTransaction.category ?? "needs_review") && styles.disabledButton,
                  ]}
                >
                  {isSavingCategory ? (
                    <ActivityIndicator color={colors.white} />
                  ) : (
                    <>
                      <Ionicons color={colors.white} name="checkmark" size={18} />
                      <Text style={styles.saveButtonText}>Save category</Text>
                    </>
                  )}
                </Pressable>
              </ScrollView>
            ) : null}
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

function TransactionRow({ item, onPress }: { item: Transaction; onPress: () => void }) {
  const isExpense = item.amount.startsWith("-");
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.row, pressed && styles.pressed]}>
      <View style={styles.rowMain}>
        <View style={styles.rowTitle}>
          <Text numberOfLines={1} style={styles.merchant}>
            {item.merchant_raw}
          </Text>
          <Text style={[styles.amount, isExpense ? styles.expense : styles.income]}>
            {formatSignedAmount(item.amount, item.currency)}
          </Text>
        </View>
        <Text numberOfLines={1} style={styles.description}>
          {item.description ?? "No description"}
        </Text>
        <View style={styles.rowMeta}>
          <Text style={styles.date}>{item.transaction_date}</Text>
          <Text style={styles.dot}>.</Text>
          <Text style={styles.category}>{labelForCategory(item.category ?? "needs_review")}</Text>
          <ConfidenceBadge transaction={item} />
        </View>
      </View>
      <Ionicons color={colors.textMuted} name="chevron-forward" size={18} />
    </Pressable>
  );
}

function ConfidenceBadge({ transaction }: { transaction: Transaction }) {
  const label = confidenceLabel(transaction);
  const isNeedsReview = transaction.category === "needs_review";
  return (
    <View style={[styles.confidenceBadge, isNeedsReview && styles.needsReviewBadge]}>
      <Text style={[styles.confidenceBadgeText, isNeedsReview && styles.needsReviewBadgeText]}>{label}</Text>
    </View>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.summaryCard}>
      <Text style={styles.summaryLabel}>{label}</Text>
      <Text style={styles.summaryValue}>{value}</Text>
    </View>
  );
}

function FilterChip({ isSelected, label, onPress }: { isSelected: boolean; label: string; onPress: () => void }) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [styles.chip, isSelected && styles.chipSelected, pressed && styles.pressed]}
    >
      <Text style={[styles.chipText, isSelected && styles.chipTextSelected]}>{label}</Text>
    </Pressable>
  );
}

function SegmentButton({ isSelected, label, onPress }: { isSelected: boolean; label: string; onPress: () => void }) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [styles.segmentButton, isSelected && styles.segmentSelected, pressed && styles.pressed]}
    >
      <Text style={[styles.segmentText, isSelected && styles.segmentTextSelected]}>{label}</Text>
    </Pressable>
  );
}

function ActionButton({
  icon,
  isLoading = false,
  label,
  onPress,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  isLoading?: boolean;
  label: string;
  onPress: () => void;
}) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.actionButton, pressed && styles.pressed]}>
      {isLoading ? <ActivityIndicator color={colors.white} /> : <Ionicons color={colors.white} name={icon} size={18} />}
      <Text style={styles.actionButtonText}>{label}</Text>
    </Pressable>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.detailRow}>
      <Text style={styles.detailLabel}>{label}</Text>
      <Text style={styles.detailValue}>{value}</Text>
    </View>
  );
}

function labelForCategory(category: string) {
  return categoryLabels[category] ?? category;
}

function confidenceLabel(transaction: Transaction) {
  if (transaction.category === "needs_review") {
    return "Needs review";
  }
  if (transaction.category_source === "manual") {
    return "Manual";
  }
  const confidence = transaction.category_confidence;
  if (confidence === null) {
    return "Unknown";
  }
  if (confidence >= 0.8) {
    return `High ${Math.round(confidence * 100)}%`;
  }
  if (confidence >= 0.6) {
    return `Medium ${Math.round(confidence * 100)}%`;
  }
  return `Low ${Math.round(confidence * 100)}%`;
}

function sourceLabel(source: string) {
  if (source === "auto") {
    return "Automatic";
  }
  if (source === "manual") {
    return "Manual";
  }
  if (source === "imported") {
    return "Imported";
  }
  return "Unknown";
}

function formatAmount(amount: string, currency: string) {
  const value = Math.abs(Number(amount));
  if (!Number.isFinite(value)) {
    return `${amount} ${currency}`;
  }
  return `${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`;
}

function formatSignedAmount(amount: string, currency: string) {
  const value = Number(amount);
  if (!Number.isFinite(value)) {
    return `${amount} ${currency}`;
  }
  const sign = value < 0 ? "-" : "+";
  return `${sign}${Math.abs(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`;
}

const styles = StyleSheet.create({
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  content: {
    gap: 16,
    padding: 20,
    paddingBottom: 116,
  },
  headerRow: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  title: {
    color: colors.text,
    ...typography.title,
  },
  subtitle: {
    color: colors.textSecondary,
    fontSize: 14,
    marginTop: 3,
  },
  summaryRow: {
    flexDirection: "row",
    gap: 10,
  },
  summaryCard: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flex: 1,
    minHeight: 82,
    padding: 14,
  },
  summaryLabel: {
    color: colors.textSecondary,
    fontSize: 13,
  },
  summaryValue: {
    color: colors.text,
    fontSize: 20,
    fontWeight: "700",
    marginTop: 8,
  },
  categorySummaryRow: {
    gap: 10,
    paddingRight: 20,
  },
  categorySummary: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    minWidth: 150,
    padding: 12,
  },
  categorySummaryLabel: {
    color: colors.textSecondary,
    fontSize: 13,
    fontWeight: "700",
  },
  categorySummaryAmount: {
    color: colors.text,
    fontSize: 17,
    fontWeight: "700",
    marginTop: 6,
  },
  categorySummaryMeta: {
    color: colors.textMuted,
    fontSize: 12,
    marginTop: 3,
  },
  filters: {
    gap: 10,
  },
  searchBox: {
    alignItems: "center",
    backgroundColor: colors.surface,
    borderColor: colors.borderStrong,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: "row",
    gap: 8,
    minHeight: 46,
    paddingHorizontal: 12,
  },
  searchInput: {
    color: colors.text,
    flex: 1,
    fontSize: 15,
  },
  chips: {
    gap: 8,
    paddingRight: 20,
  },
  chip: {
    backgroundColor: colors.surfaceRaised,
    borderColor: colors.borderStrong,
    borderRadius: radius.md,
    borderWidth: 1,
    minHeight: 36,
    justifyContent: "center",
    paddingHorizontal: 12,
  },
  chipSelected: {
    backgroundColor: colors.primaryStrong,
    borderColor: colors.primary,
  },
  chipText: {
    color: colors.textSecondary,
    fontSize: 13,
    fontWeight: "600",
  },
  chipTextSelected: {
    color: colors.white,
  },
  segmented: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    flexDirection: "row",
    gap: 4,
    padding: 4,
  },
  segmentButton: {
    alignItems: "center",
    borderRadius: 7,
    flex: 1,
    minHeight: 36,
    justifyContent: "center",
  },
  segmentSelected: {
    backgroundColor: colors.surfaceRaised,
  },
  segmentText: {
    color: colors.textSecondary,
    fontSize: 13,
    fontWeight: "700",
  },
  segmentTextSelected: {
    color: colors.primary,
  },
  filterGrid: {
    gap: 8,
  },
  filterInput: {
    backgroundColor: colors.surface,
    borderColor: colors.borderStrong,
    borderRadius: radius.md,
    borderWidth: 1,
    color: colors.text,
    fontSize: 14,
    minHeight: 44,
    paddingHorizontal: 12,
  },
  error: {
    color: colors.danger,
    fontSize: 14,
    lineHeight: 20,
  },
  message: {
    color: colors.primary,
    fontSize: 14,
  },
  list: {
    gap: 10,
  },
  row: {
    alignItems: "center",
    backgroundColor: colors.listSurface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: "row",
    gap: 10,
    minHeight: 92,
    padding: 14,
  },
  pressed: {
    opacity: 0.72,
  },
  rowMain: {
    flex: 1,
    gap: 5,
  },
  rowTitle: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: 10,
    justifyContent: "space-between",
  },
  merchant: {
    color: colors.text,
    flex: 1,
    fontSize: 16,
    fontWeight: "700",
  },
  amount: {
    flexShrink: 0,
    fontSize: 14,
    fontWeight: "800",
  },
  expense: {
    color: colors.text,
  },
  income: {
    color: colors.primary,
  },
  description: {
    color: colors.textSecondary,
    fontSize: 14,
  },
  rowMeta: {
    alignItems: "center",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 5,
  },
  date: {
    color: colors.textMuted,
    fontSize: 12,
  },
  dot: {
    color: colors.textMuted,
    fontSize: 12,
  },
  category: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: "700",
  },
  confidenceBadge: {
    backgroundColor: "rgba(52, 209, 120, 0.12)",
    borderColor: "rgba(52, 209, 120, 0.34)",
    borderRadius: radius.sm,
    borderWidth: 1,
    minHeight: 24,
    justifyContent: "center",
    paddingHorizontal: 8,
  },
  confidenceBadgeText: {
    color: colors.primary,
    fontSize: 11,
    fontWeight: "800",
  },
  needsReviewBadge: {
    backgroundColor: "rgba(242, 169, 59, 0.12)",
    borderColor: "rgba(242, 169, 59, 0.38)",
  },
  needsReviewBadgeText: {
    color: colors.amber,
  },
  emptyState: {
    alignItems: "flex-start",
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.xl,
    borderWidth: 1,
    gap: 14,
    padding: 18,
  },
  emptyTitle: {
    color: colors.text,
    fontSize: 17,
    fontWeight: "700",
    lineHeight: 24,
  },
  emptyActions: {
    gap: 10,
    width: "100%",
  },
  actionButton: {
    alignItems: "center",
    backgroundColor: colors.primaryStrong,
    borderRadius: radius.lg,
    flexDirection: "row",
    gap: 8,
    justifyContent: "center",
    minHeight: 46,
    paddingHorizontal: 14,
  },
  actionButtonText: {
    color: colors.white,
    fontSize: 15,
    fontWeight: "800",
  },
  modalBackdrop: {
    backgroundColor: "rgba(0, 0, 0, 0.64)",
    flex: 1,
    justifyContent: "flex-end",
  },
  sheet: {
    backgroundColor: colors.background,
    borderTopLeftRadius: radius.xl,
    borderTopRightRadius: radius.xl,
    maxHeight: "88%",
  },
  sheetContent: {
    gap: 14,
    padding: 20,
    paddingBottom: 30,
  },
  sheetHeader: {
    alignItems: "center",
    flexDirection: "row",
    gap: 12,
    justifyContent: "space-between",
  },
  sheetTitleBlock: {
    flex: 1,
  },
  sheetMerchant: {
    color: colors.text,
    fontSize: 22,
    fontWeight: "800",
  },
  sheetDate: {
    color: colors.textSecondary,
    fontSize: 13,
    marginTop: 4,
  },
  iconButton: {
    alignItems: "center",
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    height: 40,
    justifyContent: "center",
    width: 40,
  },
  detailAmount: {
    fontSize: 28,
    fontWeight: "800",
  },
  detailRow: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    gap: 4,
    padding: 12,
  },
  detailLabel: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: "700",
  },
  detailValue: {
    color: colors.text,
    fontSize: 15,
    lineHeight: 21,
  },
  pickerBlock: {
    gap: 10,
  },
  sectionLabel: {
    color: colors.textSecondary,
    fontSize: 14,
    fontWeight: "800",
  },
  categoryPicker: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  saveButton: {
    alignItems: "center",
    backgroundColor: colors.primaryStrong,
    borderRadius: radius.lg,
    flexDirection: "row",
    gap: 8,
    justifyContent: "center",
    minHeight: 48,
  },
  disabledButton: {
    backgroundColor: colors.textMuted,
  },
  saveButtonText: {
    color: colors.white,
    fontSize: 16,
    fontWeight: "800",
  },
});
