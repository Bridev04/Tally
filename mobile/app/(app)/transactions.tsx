import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
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
          {isLoading ? <ActivityIndicator color="#256B5B" /> : null}
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
            <Ionicons color="#7A736C" name="search" size={18} />
            <TextInput
              autoCapitalize="none"
              onChangeText={setSearch}
              placeholder="Search merchant or description"
              placeholderTextColor="#7A736C"
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
              placeholderTextColor="#7A736C"
              style={styles.filterInput}
              value={merchant}
            />
            <TextInput
              autoCapitalize="none"
              onChangeText={setDateFrom}
              placeholder="From YYYY-MM-DD"
              placeholderTextColor="#7A736C"
              style={styles.filterInput}
              value={dateFrom}
            />
            <TextInput
              autoCapitalize="none"
              onChangeText={setDateTo}
              placeholder="To YYYY-MM-DD"
              placeholderTextColor="#7A736C"
              style={styles.filterInput}
              value={dateTo}
            />
          </View>
        </View>

        {error ? <Text style={styles.error}>{error}</Text> : null}

        {!isLoading && transactions.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons color="#256B5B" name="receipt-outline" size={28} />
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
                    <Ionicons color="#38443E" name="close" size={22} />
                  </Pressable>
                </View>

                {isDetailLoading ? <ActivityIndicator color="#256B5B" /> : null}
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
                    <ActivityIndicator color="#FFFFFF" />
                  ) : (
                    <>
                      <Ionicons color="#FFFFFF" name="checkmark" size={18} />
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
      <Ionicons color="#7A736C" name="chevron-forward" size={18} />
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
      {isLoading ? <ActivityIndicator color="#FFFFFF" /> : <Ionicons color="#FFFFFF" name={icon} size={18} />}
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
    backgroundColor: "#F7F4EF",
    flex: 1,
  },
  content: {
    gap: 16,
    padding: 20,
    paddingBottom: 36,
  },
  headerRow: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  title: {
    color: "#111816",
    fontSize: 30,
    fontWeight: "700",
  },
  subtitle: {
    color: "#5F6A63",
    fontSize: 14,
    marginTop: 3,
  },
  summaryRow: {
    flexDirection: "row",
    gap: 10,
  },
  summaryCard: {
    backgroundColor: "#FFFFFF",
    borderColor: "#D8D0C7",
    borderRadius: 8,
    borderWidth: 1,
    flex: 1,
    minHeight: 82,
    padding: 14,
  },
  summaryLabel: {
    color: "#5F6A63",
    fontSize: 13,
  },
  summaryValue: {
    color: "#111816",
    fontSize: 20,
    fontWeight: "700",
    marginTop: 8,
  },
  categorySummaryRow: {
    gap: 10,
    paddingRight: 20,
  },
  categorySummary: {
    backgroundColor: "#FFFFFF",
    borderColor: "#D8D0C7",
    borderRadius: 8,
    borderWidth: 1,
    minWidth: 150,
    padding: 12,
  },
  categorySummaryLabel: {
    color: "#38443E",
    fontSize: 13,
    fontWeight: "700",
  },
  categorySummaryAmount: {
    color: "#111816",
    fontSize: 17,
    fontWeight: "700",
    marginTop: 6,
  },
  categorySummaryMeta: {
    color: "#5F6A63",
    fontSize: 12,
    marginTop: 3,
  },
  filters: {
    gap: 10,
  },
  searchBox: {
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderColor: "#D8D0C7",
    borderRadius: 8,
    borderWidth: 1,
    flexDirection: "row",
    gap: 8,
    minHeight: 46,
    paddingHorizontal: 12,
  },
  searchInput: {
    color: "#111816",
    flex: 1,
    fontSize: 15,
  },
  chips: {
    gap: 8,
    paddingRight: 20,
  },
  chip: {
    backgroundColor: "#FFFFFF",
    borderColor: "#D8D0C7",
    borderRadius: 8,
    borderWidth: 1,
    minHeight: 36,
    justifyContent: "center",
    paddingHorizontal: 12,
  },
  chipSelected: {
    backgroundColor: "#256B5B",
    borderColor: "#256B5B",
  },
  chipText: {
    color: "#38443E",
    fontSize: 13,
    fontWeight: "600",
  },
  chipTextSelected: {
    color: "#FFFFFF",
  },
  segmented: {
    backgroundColor: "#E9E2DA",
    borderRadius: 8,
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
    backgroundColor: "#FFFFFF",
  },
  segmentText: {
    color: "#5F6A63",
    fontSize: 13,
    fontWeight: "700",
  },
  segmentTextSelected: {
    color: "#111816",
  },
  filterGrid: {
    gap: 8,
  },
  filterInput: {
    backgroundColor: "#FFFFFF",
    borderColor: "#D8D0C7",
    borderRadius: 8,
    borderWidth: 1,
    color: "#111816",
    fontSize: 14,
    minHeight: 44,
    paddingHorizontal: 12,
  },
  error: {
    color: "#A23B31",
    fontSize: 14,
    lineHeight: 20,
  },
  message: {
    color: "#256B5B",
    fontSize: 14,
  },
  list: {
    gap: 10,
  },
  row: {
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderColor: "#D8D0C7",
    borderRadius: 8,
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
    color: "#111816",
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
    color: "#8F3F36",
  },
  income: {
    color: "#256B5B",
  },
  description: {
    color: "#5F6A63",
    fontSize: 14,
  },
  rowMeta: {
    alignItems: "center",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 5,
  },
  date: {
    color: "#7A736C",
    fontSize: 12,
  },
  dot: {
    color: "#B3AAA0",
    fontSize: 12,
  },
  category: {
    color: "#38443E",
    fontSize: 12,
    fontWeight: "700",
  },
  confidenceBadge: {
    backgroundColor: "#E7F1ED",
    borderColor: "#B8D2CA",
    borderRadius: 7,
    borderWidth: 1,
    minHeight: 24,
    justifyContent: "center",
    paddingHorizontal: 8,
  },
  confidenceBadgeText: {
    color: "#256B5B",
    fontSize: 11,
    fontWeight: "800",
  },
  needsReviewBadge: {
    backgroundColor: "#FFF0E0",
    borderColor: "#E5B46D",
  },
  needsReviewBadgeText: {
    color: "#8F5A15",
  },
  emptyState: {
    alignItems: "flex-start",
    backgroundColor: "#FFFFFF",
    borderColor: "#D8D0C7",
    borderRadius: 8,
    borderWidth: 1,
    gap: 14,
    padding: 18,
  },
  emptyTitle: {
    color: "#111816",
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
    backgroundColor: "#256B5B",
    borderRadius: 8,
    flexDirection: "row",
    gap: 8,
    justifyContent: "center",
    minHeight: 46,
    paddingHorizontal: 14,
  },
  actionButtonText: {
    color: "#FFFFFF",
    fontSize: 15,
    fontWeight: "800",
  },
  modalBackdrop: {
    backgroundColor: "rgba(17, 24, 22, 0.36)",
    flex: 1,
    justifyContent: "flex-end",
  },
  sheet: {
    backgroundColor: "#F7F4EF",
    borderTopLeftRadius: 8,
    borderTopRightRadius: 8,
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
    color: "#111816",
    fontSize: 22,
    fontWeight: "800",
  },
  sheetDate: {
    color: "#5F6A63",
    fontSize: 13,
    marginTop: 4,
  },
  iconButton: {
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderColor: "#D8D0C7",
    borderRadius: 8,
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
    backgroundColor: "#FFFFFF",
    borderColor: "#D8D0C7",
    borderRadius: 8,
    borderWidth: 1,
    gap: 4,
    padding: 12,
  },
  detailLabel: {
    color: "#5F6A63",
    fontSize: 12,
    fontWeight: "700",
  },
  detailValue: {
    color: "#111816",
    fontSize: 15,
    lineHeight: 21,
  },
  pickerBlock: {
    gap: 10,
  },
  sectionLabel: {
    color: "#38443E",
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
    backgroundColor: "#256B5B",
    borderRadius: 8,
    flexDirection: "row",
    gap: 8,
    justifyContent: "center",
    minHeight: 48,
  },
  disabledButton: {
    backgroundColor: "#9BA59E",
  },
  saveButtonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "800",
  },
});
