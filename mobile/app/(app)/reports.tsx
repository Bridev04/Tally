import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useAuth } from "@/context/AuthContext";
import {
  generateMonthlyReport,
  getMonthlyReports,
  loadDemoData,
  MonthlyInsightReport,
  MonthlyReportTopCategory,
} from "@/lib/api";

const colors = {
  background: "#faf9f4",
  primary: "#012d1d",
  primaryContainer: "#1b4332",
  secondary: "#256b5b",
  sage: "#b0f1cc",
  amber: "#df982d",
  text: "#1b1c19",
  muted: "#4f5a53",
  border: "#dfe4dc",
  surface: "#ffffff",
  soft: "#f5f4ef",
};

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

export default function MonthlyReportScreen() {
  const { token } = useAuth();
  const [month, setMonth] = useState(currentMonth());
  const [report, setReport] = useState<MonthlyInsightReport | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isDemoLoading, setIsDemoLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadReport = useCallback(
    async (refreshing = false) => {
      if (!token) {
        return;
      }
      if (refreshing) {
        setIsRefreshing(true);
      } else {
        setIsLoading(true);
      }
      setError(null);
      try {
        const response = await getMonthlyReports(token, { month, limit: 1 });
        setReport(response.reports[0] ?? null);
      } catch {
        setError("We couldn\u2019t load your monthly report. Please try again.");
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [month, token],
  );

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  async function handleGenerate(forceRefresh = false) {
    if (!token || isGenerating) {
      return;
    }
    setIsGenerating(true);
    setError(null);
    try {
      setReport(await generateMonthlyReport(token, month, true, forceRefresh));
    } catch {
      setError("We couldn\u2019t load your monthly report. Please try again.");
    } finally {
      setIsGenerating(false);
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
      setReport(await generateMonthlyReport(token, month, false, true));
    } catch {
      setError("We couldn\u2019t load demo data. Please try again.");
    } finally {
      setIsDemoLoading(false);
    }
  }

  const severityCounts = useMemo(() => {
    const counts = { high: 0, medium: 0, low: 0 };
    report?.anomalies.forEach((item) => {
      if (item.severity === "high" || item.severity === "medium" || item.severity === "low") {
        counts[item.severity] += 1;
      }
    });
    return counts;
  }, [report]);

  const recurringTotal = useMemo(() => {
    return report?.detected_subscriptions.reduce((total, item) => total + monthlySubscriptionAmount(item.average_amount, item.frequency), 0) ?? 0;
  }, [report]);

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl onRefresh={() => loadReport(true)} refreshing={isRefreshing} />}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.headerRow}>
          <Pressable
            accessibilityRole="button"
            onPress={() => router.push("/(app)" as never)}
            style={styles.iconButton}
          >
            <Ionicons color={colors.primary} name="chevron-back" size={24} />
          </Pressable>
          <View style={styles.headerText}>
            <Text style={styles.title}>Monthly Report</Text>
            <Text style={styles.subtitle}>A neutral summary of your imported transactions.</Text>
          </View>
        </View>

        <View style={styles.monthBar}>
          <MonthButton icon="chevron-back" onPress={() => setMonth(shiftMonth(month, -1))} />
          <Text style={styles.monthText}>{formatMonth(month)}</Text>
          <MonthButton icon="chevron-forward" onPress={() => setMonth(shiftMonth(month, 1))} />
        </View>

        {isLoading ? <ReportSkeleton /> : null}
        {!isLoading && error ? <ErrorState onRetry={() => loadReport()} /> : null}

        {!isLoading && !error && !report ? (
          <EmptyState isDemoLoading={isDemoLoading} isGenerating={isGenerating} onDemoData={handleDemoData} onGenerate={() => handleGenerate(false)} />
        ) : null}

        {!isLoading && !error && report ? (
          <>
            <MainReportCard report={report} />
            <SummaryCard report={report} />
            <TopCategories categories={report.top_categories} currency={report.currency} />
            <RecurringSection count={report.recurring_payment_count} currency={report.currency} report={report} total={recurringTotal} />
            <PatternsSection report={report} severityCounts={severityCounts} />
            <NeedsReviewSection count={report.needs_review_count} />
            <View style={styles.actionStack}>
              <PrimaryButton icon="sparkles-outline" isLoading={isGenerating} label="Generate Report" onPress={() => handleGenerate(false)} />
              <SecondaryButton icon="refresh-outline" isLoading={isGenerating} label="Refresh Report" onPress={() => handleGenerate(true)} />
              <SecondaryButton icon="home-outline" label="View Dashboard" onPress={() => router.push("/(app)" as never)} />
            </View>
          </>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

function MainReportCard({ report }: { report: MonthlyInsightReport }) {
  return (
    <View style={styles.reportCard}>
      <View style={styles.reportTop}>
        <View>
          <Text style={styles.reportLabel}>MONTHLY TOTAL</Text>
          <Text style={styles.reportMonth}>{formatMonth(report.month)}</Text>
        </View>
        <View style={styles.reportIcon}>
          <Ionicons color={colors.sage} name="document-text-outline" size={28} />
        </View>
      </View>
      <Text adjustsFontSizeToFit numberOfLines={1} style={styles.reportAmount}>
        {formatCurrency(report.total_expenses, report.currency, false)}
      </Text>
      <View style={styles.reportMetrics}>
        <InlineMetric label="Income" value={formatCurrency(report.total_income, report.currency)} />
        <InlineMetric label="Net flow" value={formatCurrency(report.net_flow, report.currency)} />
        <InlineMetric label="Transactions" value={String(report.transaction_count)} />
      </View>
    </View>
  );
}

function SummaryCard({ report }: { report: MonthlyInsightReport }) {
  return (
    <View style={styles.softPanel}>
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>Monthly Summary</Text>
        <Ionicons color={colors.secondary} name="shield-checkmark-outline" size={21} />
      </View>
      <Text style={styles.summaryText}>{report.ai_summary}</Text>
      <Text style={styles.disclaimer}>Generated from imported data only. Not financial advice.</Text>
    </View>
  );
}

function TopCategories({ categories, currency }: { categories: MonthlyReportTopCategory[]; currency: string }) {
  return (
    <View style={styles.section}>
      <SectionHeader title="Top categories" />
      {categories.length > 0 ? (
        <View style={styles.softPanel}>
          {categories.map((item) => (
            <CategoryRow currency={currency} item={item} key={item.category} />
          ))}
        </View>
      ) : (
        <EmptyLine text="Categories appear after expense rows are categorized." />
      )}
    </View>
  );
}

function CategoryRow({ currency, item }: { currency: string; item: MonthlyReportTopCategory }) {
  const percentage = Math.max(0, Math.min(100, Number(item.percentage_of_total_expenses) || 0));
  return (
    <Pressable
      accessibilityRole="button"
      onPress={() => router.push({ pathname: "/(app)/transactions", params: { category: item.category } } as never)}
      style={({ pressed }) => [styles.categoryRow, pressed && styles.pressed]}
    >
      <View style={styles.categoryHeader}>
        <View style={styles.categoryText}>
          <Text style={styles.categoryName}>{labelForCategory(item.category)}</Text>
          <Text style={styles.categoryMeta}>{item.transaction_count} transactions</Text>
        </View>
        <Text style={styles.categoryAmount}>{formatCurrency(item.total_amount, currency)}</Text>
      </View>
      <View style={styles.progressTrack}>
        <View style={[styles.progressFill, { width: `${percentage}%` }]} />
      </View>
    </Pressable>
  );
}

function RecurringSection({
  count,
  currency,
  report,
  total,
}: {
  count: number;
  currency: string;
  report: MonthlyInsightReport;
  total: number;
}) {
  return (
    <View style={styles.section}>
      <SectionHeader action="See all" title="Recurring payments" onPress={() => router.push("/(app)/recurring" as never)} />
      <View style={styles.softPanel}>
        <View style={styles.statsRow}>
          <StatPill label="Active" value={String(count)} />
          <StatPill label="Estimated monthly" value={formatCurrency(String(total), currency)} />
        </View>
        {report.detected_subscriptions.slice(0, 3).map((item) => (
          <Pressable
            accessibilityRole="button"
            key={item.merchant_name}
            onPress={() => router.push("/(app)/recurring" as never)}
            style={({ pressed }) => [styles.listRow, pressed && styles.pressed]}
          >
            <View style={styles.rowIcon}>
              <Ionicons color={colors.secondary} name="repeat-outline" size={18} />
            </View>
            <View style={styles.rowText}>
              <Text numberOfLines={1} style={styles.rowTitle}>{item.merchant_name}</Text>
              <Text style={styles.rowMeta}>{item.frequency} pattern</Text>
            </View>
            <Text style={styles.rowAmount}>{formatCurrency(item.average_amount, currency)}</Text>
          </Pressable>
        ))}
        {report.detected_subscriptions.length === 0 ? <Text style={styles.panelNote}>No active recurring payments detected yet.</Text> : null}
      </View>
    </View>
  );
}

function PatternsSection({
  report,
  severityCounts,
}: {
  report: MonthlyInsightReport;
  severityCounts: { high: number; medium: number; low: number };
}) {
  return (
    <View style={styles.section}>
      <SectionHeader action="Open insights" title="Budget leaks / patterns" onPress={() => router.push("/(app)/budget-leaks" as never)} />
      <View style={styles.softPanel}>
        <View style={styles.statsRow}>
          <StatPill label="Patterns" value={String(report.anomalies.length)} />
          <StatPill label="High" value={String(severityCounts.high)} />
          <StatPill label="Medium" value={String(severityCounts.medium)} />
          <StatPill label="Low" value={String(severityCounts.low)} />
        </View>
        {report.anomalies.slice(0, 3).map((item) => (
          <Pressable
            accessibilityRole="button"
            key={`${item.anomaly_type}-${item.explanation}`}
            onPress={() => router.push("/(app)/budget-leaks" as never)}
            style={({ pressed }) => [styles.patternRow, pressed && styles.pressed]}
          >
            <View style={styles.patternDot} />
            <Text numberOfLines={2} style={styles.patternCopy}>{item.explanation}</Text>
          </Pressable>
        ))}
        {report.anomalies.length === 0 ? <Text style={styles.panelNote}>No budget leak patterns included for this report.</Text> : null}
      </View>
    </View>
  );
}

function NeedsReviewSection({ count }: { count: number }) {
  return (
    <View style={styles.softPanel}>
      <View style={styles.sectionHeader}>
        <View>
          <Text style={styles.sectionTitle}>Needs review</Text>
          <Text style={styles.panelNote}>{count} transactions may need category review.</Text>
        </View>
        <Pressable
          accessibilityRole="button"
          onPress={() => router.push({ pathname: "/(app)/transactions", params: { category: "needs_review" } } as never)}
          style={({ pressed }) => [styles.smallButton, pressed && styles.pressed]}
        >
          <Text style={styles.smallButtonText}>Open</Text>
        </Pressable>
      </View>
    </View>
  );
}

function EmptyState({
  isDemoLoading,
  isGenerating,
  onDemoData,
  onGenerate,
}: {
  isDemoLoading: boolean;
  isGenerating: boolean;
  onDemoData: () => void;
  onGenerate: () => void;
}) {
  return (
    <View style={styles.emptyState}>
      <View style={styles.emptyIcon}>
        <Ionicons color={colors.secondary} name="document-text-outline" size={28} />
      </View>
      <Text style={styles.emptyTitle}>No report available yet.</Text>
      <Text style={styles.emptyCopy}>Import transactions or try demo data to generate your monthly report.</Text>
      <PrimaryButton icon="sparkles-outline" isLoading={isGenerating} label="Generate Report" onPress={onGenerate} />
      <SecondaryButton icon="add-circle-outline" label="Import Transactions" onPress={() => router.push("/(app)/import" as never)} />
      <SecondaryButton icon="sparkles-outline" isLoading={isDemoLoading} label="Try Demo Data" onPress={onDemoData} />
    </View>
  );
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <View style={styles.errorPanel}>
      <Text style={styles.errorTitle}>We couldn\u2019t load your monthly report. Please try again.</Text>
      <SecondaryButton icon="refresh-outline" label="Retry" onPress={onRetry} />
    </View>
  );
}

function ReportSkeleton() {
  return (
    <View style={styles.skeletonStack}>
      <View style={[styles.skeleton, styles.skeletonHero]} />
      <View style={[styles.skeleton, styles.skeletonSummary]} />
      <View style={[styles.skeleton, styles.skeletonSummary]} />
    </View>
  );
}

function SectionHeader({ action, onPress, title }: { action?: string; onPress?: () => void; title: string }) {
  return (
    <View style={styles.sectionHeader}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {action && onPress ? (
        <Pressable accessibilityRole="button" hitSlop={10} onPress={onPress}>
          <Text style={styles.sectionAction}>{action}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

function PrimaryButton({
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
    <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.primaryButton, pressed && styles.pressed]}>
      {isLoading ? <ActivityIndicator color="#ffffff" /> : <Ionicons color="#ffffff" name={icon} size={18} />}
      <Text style={styles.primaryButtonText}>{label}</Text>
    </Pressable>
  );
}

function SecondaryButton({
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
    <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.secondaryButton, pressed && styles.pressed]}>
      {isLoading ? <ActivityIndicator color={colors.primary} /> : <Ionicons color={colors.primary} name={icon} size={18} />}
      <Text style={styles.secondaryButtonText}>{label}</Text>
    </Pressable>
  );
}

function MonthButton({ icon, onPress }: { icon: keyof typeof Ionicons.glyphMap; onPress: () => void }) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.monthButton, pressed && styles.pressed]}>
      <Ionicons color={colors.primary} name={icon} size={20} />
    </Pressable>
  );
}

function InlineMetric({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.inlineMetric}>
      <Text style={styles.inlineLabel}>{label}</Text>
      <Text adjustsFontSizeToFit numberOfLines={1} style={styles.inlineValue}>{value}</Text>
    </View>
  );
}

function StatPill({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.statPill}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

function EmptyLine({ text }: { text: string }) {
  return (
    <View style={styles.softPanel}>
      <Text style={styles.panelNote}>{text}</Text>
    </View>
  );
}

function labelForCategory(category: string) {
  return categoryLabels[category] ?? category.replace(/_/g, " ");
}

function currentMonth() {
  const value = new Date();
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}`;
}

function shiftMonth(month: string, delta: number) {
  const [year, monthNumber] = month.split("-").map(Number);
  const value = new Date(year, monthNumber - 1 + delta, 1);
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}`;
}

function formatMonth(month: string) {
  const dateValue = new Date(`${month}-01T00:00:00`);
  return dateValue.toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

function formatCurrency(amount: string, currency: string, keepSign = true) {
  const value = Number(amount);
  if (!Number.isFinite(value)) {
    return `${amount} ${currency}`;
  }
  const symbol = currency === "PHP" ? "\u20b1" : `${currency} `;
  const sign = keepSign && value < 0 ? "-" : "";
  return `${sign}${symbol}${Math.abs(value).toLocaleString(undefined, {
    maximumFractionDigits: 0,
    minimumFractionDigits: 0,
  })}`;
}

function monthlySubscriptionAmount(amount: string, frequency: string) {
  const value = Number(amount);
  if (!Number.isFinite(value)) {
    return 0;
  }
  if (frequency === "weekly") {
    return (value * 52) / 12;
  }
  if (frequency === "biweekly") {
    return (value * 26) / 12;
  }
  if (frequency === "yearly") {
    return value / 12;
  }
  return value;
}

const styles = StyleSheet.create({
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  content: {
    gap: 20,
    padding: 20,
    paddingBottom: 116,
  },
  headerRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: 12,
  },
  iconButton: {
    alignItems: "center",
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: 16,
    borderWidth: 1,
    height: 48,
    justifyContent: "center",
    width: 48,
  },
  headerText: {
    flex: 1,
    gap: 3,
  },
  title: {
    color: colors.text,
    fontSize: 31,
    fontWeight: "900",
    letterSpacing: 0,
  },
  subtitle: {
    color: colors.muted,
    fontSize: 15,
    lineHeight: 21,
  },
  monthBar: {
    alignItems: "center",
    backgroundColor: colors.soft,
    borderRadius: 18,
    flexDirection: "row",
    justifyContent: "space-between",
    minHeight: 56,
    padding: 6,
  },
  monthButton: {
    alignItems: "center",
    backgroundColor: colors.surface,
    borderRadius: 14,
    height: 44,
    justifyContent: "center",
    width: 44,
  },
  monthText: {
    color: colors.primary,
    flex: 1,
    fontSize: 17,
    fontWeight: "900",
    textAlign: "center",
  },
  reportCard: {
    backgroundColor: colors.primaryContainer,
    borderRadius: 30,
    gap: 20,
    overflow: "hidden",
    padding: 24,
    shadowColor: colors.primary,
    shadowOpacity: 0.12,
    shadowRadius: 24,
  },
  reportTop: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  reportLabel: {
    color: "#dce8df",
    fontSize: 13,
    fontWeight: "900",
  },
  reportMonth: {
    color: colors.sage,
    fontSize: 16,
    fontWeight: "900",
    marginTop: 4,
  },
  reportIcon: {
    alignItems: "center",
    backgroundColor: "rgba(255, 255, 255, 0.08)",
    borderRadius: 30,
    height: 60,
    justifyContent: "center",
    width: 60,
  },
  reportAmount: {
    color: "#ffffff",
    fontSize: 54,
    fontWeight: "900",
    letterSpacing: 0,
  },
  reportMetrics: {
    flexDirection: "row",
    gap: 8,
  },
  inlineMetric: {
    backgroundColor: "rgba(255, 255, 255, 0.08)",
    borderRadius: 14,
    flex: 1,
    minHeight: 64,
    padding: 10,
  },
  inlineLabel: {
    color: "#dce8df",
    fontSize: 11,
    fontWeight: "800",
  },
  inlineValue: {
    color: "#ffffff",
    fontSize: 16,
    fontWeight: "900",
    marginTop: 7,
  },
  section: {
    gap: 12,
  },
  sectionHeader: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  sectionTitle: {
    color: colors.text,
    fontSize: 23,
    fontWeight: "900",
  },
  sectionAction: {
    color: colors.secondary,
    fontSize: 12,
    fontWeight: "900",
    textTransform: "uppercase",
  },
  softPanel: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: 22,
    borderWidth: 1,
    gap: 14,
    padding: 16,
  },
  summaryText: {
    color: colors.text,
    fontSize: 16,
    lineHeight: 24,
  },
  disclaimer: {
    color: colors.muted,
    fontSize: 12,
    fontWeight: "800",
  },
  categoryRow: {
    gap: 10,
  },
  categoryHeader: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: 10,
    justifyContent: "space-between",
  },
  categoryText: {
    flex: 1,
    gap: 3,
  },
  categoryName: {
    color: colors.text,
    fontSize: 16,
    fontWeight: "900",
  },
  categoryMeta: {
    color: colors.muted,
    fontSize: 13,
  },
  categoryAmount: {
    color: colors.secondary,
    fontSize: 15,
    fontWeight: "900",
  },
  progressTrack: {
    backgroundColor: "#edf0eb",
    borderRadius: 99,
    height: 9,
    overflow: "hidden",
  },
  progressFill: {
    backgroundColor: colors.secondary,
    borderRadius: 99,
    height: 9,
  },
  statsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  statPill: {
    backgroundColor: colors.soft,
    borderRadius: 14,
    minWidth: "22%",
    padding: 10,
  },
  statValue: {
    color: colors.text,
    fontSize: 18,
    fontWeight: "900",
  },
  statLabel: {
    color: colors.muted,
    fontSize: 11,
    fontWeight: "800",
    marginTop: 2,
  },
  listRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: 12,
    minHeight: 58,
  },
  rowIcon: {
    alignItems: "center",
    backgroundColor: "#eaf5ef",
    borderRadius: 14,
    height: 42,
    justifyContent: "center",
    width: 42,
  },
  rowText: {
    flex: 1,
    gap: 3,
  },
  rowTitle: {
    color: colors.text,
    fontSize: 16,
    fontWeight: "900",
  },
  rowMeta: {
    color: colors.muted,
    fontSize: 13,
  },
  rowAmount: {
    color: colors.text,
    fontSize: 14,
    fontWeight: "900",
  },
  patternRow: {
    flexDirection: "row",
    gap: 10,
  },
  patternDot: {
    backgroundColor: colors.amber,
    borderRadius: 5,
    height: 10,
    marginTop: 8,
    width: 10,
  },
  patternCopy: {
    color: colors.text,
    flex: 1,
    fontSize: 15,
    lineHeight: 21,
  },
  panelNote: {
    color: colors.muted,
    fontSize: 14,
    lineHeight: 20,
  },
  smallButton: {
    alignItems: "center",
    backgroundColor: colors.sage,
    borderRadius: 14,
    justifyContent: "center",
    minHeight: 42,
    paddingHorizontal: 18,
  },
  smallButtonText: {
    color: colors.primary,
    fontSize: 14,
    fontWeight: "900",
  },
  actionStack: {
    gap: 10,
  },
  primaryButton: {
    alignItems: "center",
    backgroundColor: colors.primaryContainer,
    borderRadius: 16,
    flexDirection: "row",
    gap: 8,
    justifyContent: "center",
    minHeight: 50,
    paddingHorizontal: 16,
    width: "100%",
  },
  primaryButtonText: {
    color: "#ffffff",
    fontSize: 15,
    fontWeight: "900",
  },
  secondaryButton: {
    alignItems: "center",
    backgroundColor: colors.sage,
    borderRadius: 16,
    flexDirection: "row",
    gap: 8,
    justifyContent: "center",
    minHeight: 50,
    paddingHorizontal: 16,
    width: "100%",
  },
  secondaryButtonText: {
    color: colors.primary,
    fontSize: 15,
    fontWeight: "900",
  },
  emptyState: {
    alignItems: "flex-start",
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: 24,
    borderWidth: 1,
    gap: 14,
    padding: 20,
  },
  emptyIcon: {
    alignItems: "center",
    backgroundColor: "#eaf5ef",
    borderRadius: 28,
    height: 56,
    justifyContent: "center",
    width: 56,
  },
  emptyTitle: {
    color: colors.text,
    fontSize: 22,
    fontWeight: "900",
  },
  emptyCopy: {
    color: colors.muted,
    fontSize: 16,
    lineHeight: 23,
  },
  errorPanel: {
    backgroundColor: "#fff8ec",
    borderColor: "#efc37b",
    borderRadius: 20,
    borderWidth: 1,
    gap: 12,
    padding: 18,
  },
  errorTitle: {
    color: colors.text,
    fontSize: 16,
    fontWeight: "900",
  },
  skeletonStack: {
    gap: 14,
  },
  skeleton: {
    backgroundColor: "#eceee8",
    borderRadius: 24,
  },
  skeletonHero: {
    height: 220,
  },
  skeletonSummary: {
    height: 128,
  },
  pressed: {
    opacity: 0.72,
  },
});
