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
  DashboardAnomalyItem,
  DashboardRecentTransaction,
  DashboardSubscriptionItem,
  DashboardSummaryResponse,
  DashboardTopCategory,
  getDashboardSummary,
  loadDemoData,
} from "@/lib/api";

const colors = {
  background: "#faf9f4",
  primary: "#012d1d",
  primaryContainer: "#1b4332",
  secondary: "#2b694d",
  sage: "#b0f1cc",
  amber: "#df982d",
  text: "#1b1c19",
  muted: "#414844",
  outline: "#c1c8c2",
  surface: "#ffffff",
  softSurface: "#f5f4ef",
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

function greetingForHour(hour: number) {
  if (hour < 12) {
    return "Good morning";
  }
  if (hour < 18) {
    return "Good afternoon";
  }
  return "Good evening";
}

export default function HomeScreen() {
  const { token, user } = useAuth();
  const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isDemoLoading, setIsDemoLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = useCallback(
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
        setSummary(await getDashboardSummary(token));
      } catch {
        setError("We couldn’t load your dashboard. Please try again.");
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [token],
  );

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  async function handleDemoData() {
    if (!token || isDemoLoading) {
      return;
    }
    setIsDemoLoading(true);
    setError(null);
    try {
      await loadDemoData(token);
      await loadDashboard();
    } catch {
      setError("We couldn’t load demo data. Please try again.");
    } finally {
      setIsDemoLoading(false);
    }
  }

  const firstName = useMemo(() => {
    const emailName = user?.email?.split("@")[0]?.trim();
    if (!emailName) {
      return "";
    }
    return emailName.split(/[._-]/)[0]?.replace(/^\w/, (value) => value.toUpperCase()) ?? "";
  }, [user?.email]);

  const greeting = useMemo(() => greetingForHour(new Date().getHours()), []);
  const insight = summary?.anomaly_summary.latest_items[0] ?? null;

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            colors={[colors.primaryContainer]}
            onRefresh={() => loadDashboard(true)}
            refreshing={isRefreshing}
            tintColor={colors.primaryContainer}
          />
        }
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.topBar}>
          <Pressable
            accessibilityLabel="Open profile"
            accessibilityRole="button"
            onPress={() => router.push("/(app)/settings" as never)}
            style={styles.iconButton}
          >
            <Ionicons color={colors.primary} name="menu-outline" size={28} />
          </Pressable>
          <Text style={styles.brand}>Tally</Text>
          <Pressable
            accessibilityLabel="Open insights"
            accessibilityRole="button"
            onPress={() => router.push("/(app)/budget-leaks" as never)}
            style={styles.iconButton}
          >
            <Ionicons color={colors.primary} name="notifications-outline" size={25} />
          </Pressable>
        </View>

        <View style={styles.greetingBlock}>
          <Text style={styles.greeting}>{firstName ? `${greeting}, ${firstName}` : greeting}</Text>
          <Text style={styles.greetingCopy}>Here’s your financial pulse.</Text>
        </View>

        {isLoading ? <DashboardSkeleton /> : null}
        {!isLoading && error ? <ErrorState onRetry={() => loadDashboard()} /> : null}
        {!isLoading && !error && summary && !summary.has_data ? (
          <EmptyDashboardState isDemoLoading={isDemoLoading} onDemoData={handleDemoData} />
        ) : null}

        {!isLoading && !error && summary?.has_data ? (
          <>
            <PulseCard summary={summary} />
            <InsightPreviewCard insight={insight} />
            <MonthlyReportPreview summary={summary} />
            <SummaryGrid summary={summary} />
            <UpcomingCharges currency={summary.currency} items={summary.subscription_summary.upcoming_items} />
            <TopCategories categories={summary.top_categories} currency={summary.currency} total={summary.total_expenses} />
            <RecentTransactions items={summary.recent_transactions} currency={summary.currency} />
            <SpendingInsights summary={summary} />
          </>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

function PulseCard({ summary }: { summary: DashboardSummaryResponse }) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={() => router.push("/(app)/transactions" as never)}
      style={({ pressed }) => [styles.pulseCard, pressed && styles.pressed]}
    >
      <View style={styles.waveOne} />
      <View style={styles.waveTwo} />
      <View style={styles.pulseHeader}>
        <View>
          <Text style={styles.pulseLabel}>TOTAL SPENDING</Text>
          <Text style={styles.pulsePeriod}>{formatMonth(summary.month)}</Text>
        </View>
        <View style={styles.pulseArrow}>
          <Ionicons color="#bde7cd" name="trending-up-outline" size={28} />
        </View>
      </View>
      <Text adjustsFontSizeToFit numberOfLines={1} style={styles.pulseAmount}>
        {formatCurrency(summary.total_expenses, summary.currency, false)}
      </Text>
      <Text style={styles.pulseCopy}>Based on imported transactions</Text>
    </Pressable>
  );
}

function InsightPreviewCard({ insight }: { insight: DashboardAnomalyItem | null }) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={() => router.push("/(app)/budget-leaks" as never)}
      style={({ pressed }) => [styles.insightCard, pressed && styles.pressed]}
    >
      <View style={styles.insightIcon}>
        <Ionicons color={colors.secondary} name="leaf-outline" size={26} />
      </View>
      <View style={styles.insightText}>
        <Text style={styles.insightLabel}>INSIGHT</Text>
        <Text numberOfLines={2} style={styles.insightCopy}>
          {insight?.explanation ?? "No budget leaks detected for this period."}
        </Text>
      </View>
      <Ionicons color="#748078" name="chevron-forward" size={28} />
    </Pressable>
  );
}

function MonthlyReportPreview({ summary }: { summary: DashboardSummaryResponse }) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={() => router.push("/(app)/reports" as never)}
      style={({ pressed }) => [styles.reportPreview, pressed && styles.pressed]}
    >
      <View style={styles.reportPreviewIcon}>
        <Ionicons color={colors.secondary} name="document-text-outline" size={24} />
      </View>
      <View style={styles.insightText}>
        <Text style={styles.insightLabel}>MONTHLY REPORT</Text>
        <Text numberOfLines={2} style={styles.insightCopy}>
          Review {formatMonth(summary.month)} totals, recurring payments, and neutral spending patterns.
        </Text>
      </View>
      <Ionicons color="#748078" name="chevron-forward" size={28} />
    </Pressable>
  );
}

function SummaryGrid({ summary }: { summary: DashboardSummaryResponse }) {
  return (
    <View style={styles.metricGrid}>
      <MetricCard icon="wallet-outline" label="Income" value={formatCurrency(summary.total_income, summary.currency)} />
      <MetricCard icon="pulse-outline" label="Net flow" value={formatCurrency(summary.net_flow, summary.currency)} />
      <MetricCard icon="receipt-outline" label="Transactions" value={String(summary.transaction_count)} />
      <MetricCard icon="alert-circle-outline" label="Needs review" tone="watch" value={String(summary.needs_review_count)} />
    </View>
  );
}

function MetricCard({
  icon,
  label,
  tone = "normal",
  value,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  tone?: "normal" | "watch";
  value: string;
}) {
  return (
    <View style={[styles.metricCard, tone === "watch" && styles.metricWatch]}>
      <View style={styles.metricTop}>
        <Text style={styles.metricLabel}>{label}</Text>
        <Ionicons color={tone === "watch" ? colors.amber : colors.secondary} name={icon} size={17} />
      </View>
      <Text adjustsFontSizeToFit numberOfLines={1} style={styles.metricValue}>
        {value}
      </Text>
    </View>
  );
}

function UpcomingCharges({ currency, items }: { currency: string; items: DashboardSubscriptionItem[] }) {
  return (
    <View style={styles.section}>
      <SectionHeader action="See all" title="Upcoming charges" onPress={() => router.push("/(app)/recurring" as never)} />
      {items.length > 0 ? (
        <View style={styles.cardStack}>
          {items.map((item) => (
            <Pressable
              accessibilityRole="button"
              key={item.id}
              onPress={() => router.push("/(app)/recurring" as never)}
              style={({ pressed }) => [styles.chargeRow, pressed && styles.pressed]}
            >
              <View style={styles.merchantMark}>
                <Text numberOfLines={1} style={styles.merchantInitial}>
                  {item.merchant_name.slice(0, 1).toUpperCase()}
                </Text>
              </View>
              <View style={styles.rowText}>
                <Text numberOfLines={1} style={styles.rowTitle}>
                  {item.merchant_name}
                </Text>
                <Text style={styles.rowMeta}>{formatDate(item.next_expected_date)}</Text>
              </View>
              <Text style={styles.rowAmount}>{formatCurrency(item.average_amount, currency)}</Text>
              <Ionicons color="#748078" name="chevron-forward" size={20} />
            </Pressable>
          ))}
        </View>
      ) : (
        <SoftEmptyLine text="No upcoming recurring charges detected yet." />
      )}
    </View>
  );
}

function TopCategories({
  categories,
  currency,
  total,
}: {
  categories: DashboardTopCategory[];
  currency: string;
  total: string;
}) {
  return (
    <View style={styles.section}>
      <SectionHeader title="Top categories" />
      {categories.length > 0 ? (
        <View style={styles.softPanel}>
          {categories.map((item) => (
            <CategoryProgressRow currency={currency} item={item} key={item.category} />
          ))}
          <Text style={styles.panelNote}>Based on {formatCurrency(total, currency)} in imported expenses.</Text>
        </View>
      ) : (
        <SoftEmptyLine text="Categories will appear after imported expense rows are categorized." />
      )}
    </View>
  );
}

function CategoryProgressRow({ currency, item }: { currency: string; item: DashboardTopCategory }) {
  const percentage = Math.max(0, Math.min(100, Number(item.percentage_of_total_expenses) || 0));
  return (
    <Pressable
      accessibilityRole="button"
      onPress={() => router.push("/(app)/transactions" as never)}
      style={({ pressed }) => [styles.categoryRow, pressed && styles.pressed]}
    >
      <View style={styles.categoryHeader}>
        <View style={styles.categoryTitleBlock}>
          <Text style={styles.categoryName}>{labelForCategory(item.category)}</Text>
          <Text style={styles.categoryMeta}>
            {item.transaction_count} transactions • {percentage.toFixed(0)}%
          </Text>
        </View>
        <Text style={styles.categoryAmount}>{formatCurrency(item.total_amount, currency)}</Text>
      </View>
      <View style={styles.progressTrack}>
        <View style={[styles.progressFill, { width: `${percentage}%` }]} />
      </View>
    </Pressable>
  );
}

function RecentTransactions({ currency, items }: { currency: string; items: DashboardRecentTransaction[] }) {
  return (
    <View style={styles.section}>
      <SectionHeader action="View all" title="Recent transactions" onPress={() => router.push("/(app)/transactions" as never)} />
      {items.length > 0 ? (
        <View style={styles.softPanel}>
          {items.map((item) => (
            <Pressable
              accessibilityRole="button"
              key={item.id}
              onPress={() => router.push("/(app)/transactions" as never)}
              style={({ pressed }) => [styles.transactionRow, pressed && styles.pressed]}
            >
              <View style={styles.transactionIcon}>
                <Ionicons color={colors.secondary} name="receipt-outline" size={18} />
              </View>
              <View style={styles.rowText}>
                <Text numberOfLines={1} style={styles.rowTitle}>
                  {item.merchant_normalized ?? "Imported transaction"}
                </Text>
                <Text style={styles.rowMeta}>
                  {formatShortDate(item.transaction_date)} • {labelForCategory(item.category ?? "needs_review")}
                </Text>
              </View>
              <Text style={styles.rowAmount}>{formatCurrency(item.amount, currency, true)}</Text>
            </Pressable>
          ))}
        </View>
      ) : (
        <SoftEmptyLine text="Recent imported transactions will appear here." />
      )}
    </View>
  );
}

function SpendingInsights({ summary }: { summary: DashboardSummaryResponse }) {
  const anomalies = summary.anomaly_summary.latest_items;
  return (
    <View style={styles.section}>
      <SectionHeader title="Spending insights" />
      <View style={styles.softPanel}>
        <View style={styles.insightStats}>
          <MetricPill label="Detected pattern" value={String(summary.anomaly_summary.total_count)} />
          <MetricPill label="High" value={String(summary.anomaly_summary.high_count)} />
          <MetricPill label="Medium" value={String(summary.anomaly_summary.medium_count)} />
          <MetricPill label="Low" value={String(summary.anomaly_summary.low_count)} />
        </View>
        {anomalies.length > 0 ? (
          anomalies.map((item) => (
            <Pressable
              accessibilityRole="button"
              key={item.id}
              onPress={() => router.push("/(app)/budget-leaks" as never)}
              style={({ pressed }) => [styles.anomalyLine, pressed && styles.pressed]}
            >
              <View style={styles.anomalyDot} />
              <View style={styles.rowText}>
                <Text style={styles.anomalyLabel}>May be worth reviewing</Text>
                <Text numberOfLines={2} style={styles.anomalyCopy}>
                  {item.explanation}
                </Text>
              </View>
            </Pressable>
          ))
        ) : (
          <Text style={styles.panelNote}>No budget leaks detected for this period. Based on imported transactions.</Text>
        )}
      </View>
    </View>
  );
}

function MetricPill({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.metricPill}>
      <Text style={styles.metricPillValue}>{value}</Text>
      <Text style={styles.metricPillLabel}>{label}</Text>
    </View>
  );
}

function EmptyDashboardState({
  isDemoLoading,
  onDemoData,
}: {
  isDemoLoading: boolean;
  onDemoData: () => void;
}) {
  return (
    <View style={styles.emptyState}>
      <View style={styles.emptyIcon}>
        <Ionicons color={colors.secondary} name="sparkles-outline" size={30} />
      </View>
      <Text style={styles.emptyTitle}>No imported transactions yet.</Text>
      <Text style={styles.emptyCopy}>Import transactions or try demo data to see your Tally dashboard.</Text>
      <Pressable
        accessibilityRole="button"
        onPress={() => router.push("/(app)/import" as never)}
        style={({ pressed }) => [styles.primaryButton, pressed && styles.pressed]}
      >
        <Ionicons color="#ffffff" name="add-circle-outline" size={18} />
        <Text style={styles.primaryButtonText}>Import transactions</Text>
      </Pressable>
      <Pressable
        accessibilityRole="button"
        onPress={onDemoData}
        style={({ pressed }) => [styles.secondaryButton, pressed && styles.pressed]}
      >
        {isDemoLoading ? <ActivityIndicator color={colors.primary} /> : <Ionicons color={colors.primary} name="sparkles-outline" size={18} />}
        <Text style={styles.secondaryButtonText}>Try Demo Data</Text>
      </Pressable>
    </View>
  );
}

function DashboardSkeleton() {
  return (
    <View style={styles.skeletonStack}>
      <View style={[styles.skeleton, styles.skeletonHero]} />
      <View style={[styles.skeleton, styles.skeletonInsight]} />
      <View style={styles.metricGrid}>
        {[0, 1, 2, 3].map((item) => (
          <View key={item} style={[styles.skeleton, styles.skeletonMetric]} />
        ))}
      </View>
    </View>
  );
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <View style={styles.errorPanel}>
      <Text style={styles.errorTitle}>We couldn’t load your dashboard. Please try again.</Text>
      <Pressable accessibilityRole="button" onPress={onRetry} style={({ pressed }) => [styles.secondaryButton, pressed && styles.pressed]}>
        <Ionicons color={colors.primary} name="refresh-outline" size={18} />
        <Text style={styles.secondaryButtonText}>Retry</Text>
      </Pressable>
    </View>
  );
}

function SectionHeader({ action, onPress, title }: { action?: string; onPress?: () => void; title: string }) {
  return (
    <View style={styles.sectionHeader}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {action && onPress ? (
        <Pressable accessibilityRole="button" onPress={onPress} hitSlop={10}>
          <Text style={styles.sectionAction}>{action}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

function SoftEmptyLine({ text }: { text: string }) {
  return (
    <View style={styles.softPanel}>
      <Text style={styles.panelNote}>{text}</Text>
    </View>
  );
}

function labelForCategory(category: string) {
  return categoryLabels[category] ?? category.replace(/_/g, " ");
}

function formatCurrency(amount: string, currency: string, keepSign = true) {
  const value = Number(amount);
  if (!Number.isFinite(value)) {
    return `${amount} ${currency}`;
  }
  const sign = keepSign && value < 0 ? "-" : "";
  const symbol = currency === "PHP" ? "₱" : `${currency} `;
  return `${sign}${symbol}${Math.abs(value).toLocaleString(undefined, {
    maximumFractionDigits: 0,
    minimumFractionDigits: 0,
  })}`;
}

function formatDate(value: string | null) {
  if (!value) {
    return "Expected date unavailable";
  }
  const dateValue = new Date(`${value}T00:00:00`);
  return dateValue.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function formatShortDate(value: string) {
  const dateValue = new Date(`${value}T00:00:00`);
  return dateValue.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function formatMonth(value: string | null) {
  if (!value) {
    return "Latest month";
  }
  const dateValue = new Date(`${value}-01T00:00:00`);
  return dateValue.toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

const styles = StyleSheet.create({
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  content: {
    gap: 24,
    padding: 20,
    paddingBottom: 116,
  },
  topBar: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
    minHeight: 44,
  },
  iconButton: {
    alignItems: "center",
    height: 44,
    justifyContent: "center",
    width: 44,
  },
  brand: {
    color: colors.primary,
    flex: 1,
    fontSize: 31,
    fontWeight: "800",
    marginLeft: 8,
  },
  greetingBlock: {
    gap: 6,
    marginTop: 22,
  },
  greeting: {
    color: colors.text,
    fontSize: 34,
    fontWeight: "800",
    letterSpacing: 0,
    lineHeight: 40,
  },
  greetingCopy: {
    color: colors.muted,
    fontSize: 19,
    lineHeight: 26,
  },
  pulseCard: {
    backgroundColor: colors.primaryContainer,
    borderRadius: 30,
    minHeight: 216,
    overflow: "hidden",
    padding: 26,
    shadowColor: colors.primary,
    shadowOpacity: 0.12,
    shadowRadius: 24,
  },
  waveOne: {
    borderColor: "rgba(176, 241, 204, 0.16)",
    borderRadius: 220,
    borderWidth: 4,
    bottom: 42,
    height: 120,
    left: 36,
    position: "absolute",
    transform: [{ rotate: "-8deg" }],
    width: 420,
  },
  waveTwo: {
    borderColor: "rgba(176, 241, 204, 0.12)",
    borderRadius: 220,
    borderWidth: 2,
    bottom: 8,
    height: 104,
    left: 32,
    position: "absolute",
    transform: [{ rotate: "-8deg" }],
    width: 420,
  },
  pulseHeader: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  pulseLabel: {
    color: "#d5ded7",
    fontSize: 14,
    fontWeight: "800",
    letterSpacing: 0,
  },
  pulsePeriod: {
    color: colors.sage,
    fontSize: 15,
    fontWeight: "800",
    marginTop: 4,
  },
  pulseArrow: {
    alignItems: "center",
    backgroundColor: "rgba(255, 255, 255, 0.07)",
    borderRadius: 34,
    height: 68,
    justifyContent: "center",
    width: 68,
  },
  pulseAmount: {
    color: "#ffffff",
    fontSize: 58,
    fontWeight: "900",
    letterSpacing: 0,
    marginTop: 8,
  },
  pulseCopy: {
    color: "#d5ded7",
    fontSize: 17,
    fontWeight: "700",
    marginTop: 20,
  },
  insightCard: {
    alignItems: "center",
    backgroundColor: colors.softSurface,
    borderRadius: 26,
    flexDirection: "row",
    gap: 18,
    minHeight: 112,
    padding: 18,
  },
  reportPreview: {
    alignItems: "center",
    backgroundColor: colors.surface,
    borderColor: "#e6e8e2",
    borderRadius: 22,
    borderWidth: 1,
    flexDirection: "row",
    gap: 16,
    minHeight: 104,
    padding: 16,
  },
  reportPreviewIcon: {
    alignItems: "center",
    backgroundColor: "#eaf5ef",
    borderRadius: 34,
    height: 58,
    justifyContent: "center",
    width: 58,
  },
  insightIcon: {
    alignItems: "center",
    backgroundColor: colors.sage,
    borderRadius: 40,
    height: 66,
    justifyContent: "center",
    width: 66,
  },
  insightText: {
    flex: 1,
    gap: 5,
  },
  insightLabel: {
    color: colors.secondary,
    fontSize: 15,
    fontWeight: "900",
    letterSpacing: 2,
  },
  insightCopy: {
    color: colors.text,
    fontSize: 19,
    fontWeight: "600",
    lineHeight: 26,
  },
  metricGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 12,
  },
  metricCard: {
    backgroundColor: colors.surface,
    borderColor: "#e6e8e2",
    borderRadius: 18,
    borderWidth: 1,
    flexGrow: 1,
    minHeight: 94,
    padding: 15,
    width: "47%",
  },
  metricWatch: {
    backgroundColor: "#fff8ec",
    borderColor: "#efc37b",
  },
  metricTop: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  metricLabel: {
    color: colors.muted,
    fontSize: 13,
    fontWeight: "700",
  },
  metricValue: {
    color: colors.text,
    fontSize: 22,
    fontWeight: "900",
    marginTop: 14,
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
    fontSize: 25,
    fontWeight: "800",
  },
  sectionAction: {
    color: colors.secondary,
    fontSize: 13,
    fontWeight: "900",
    letterSpacing: 1.5,
    textTransform: "uppercase",
  },
  cardStack: {
    gap: 12,
  },
  chargeRow: {
    alignItems: "center",
    backgroundColor: colors.surface,
    borderRadius: 22,
    flexDirection: "row",
    gap: 14,
    minHeight: 88,
    padding: 16,
  },
  merchantMark: {
    alignItems: "center",
    backgroundColor: "#0d1712",
    borderRadius: 16,
    height: 58,
    justifyContent: "center",
    width: 58,
  },
  merchantInitial: {
    color: colors.sage,
    fontSize: 24,
    fontWeight: "900",
  },
  rowText: {
    flex: 1,
    gap: 3,
  },
  rowTitle: {
    color: colors.text,
    fontSize: 18,
    fontWeight: "800",
    textTransform: "capitalize",
  },
  rowMeta: {
    color: colors.muted,
    fontSize: 14,
  },
  rowAmount: {
    color: colors.text,
    flexShrink: 0,
    fontSize: 16,
    fontWeight: "900",
  },
  softPanel: {
    backgroundColor: colors.surface,
    borderColor: "#e6e8e2",
    borderRadius: 22,
    borderWidth: 1,
    gap: 14,
    padding: 16,
  },
  categoryRow: {
    gap: 10,
  },
  categoryHeader: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: 12,
    justifyContent: "space-between",
  },
  categoryTitleBlock: {
    flex: 1,
    gap: 3,
  },
  categoryName: {
    color: colors.text,
    fontSize: 16,
    fontWeight: "800",
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
  panelNote: {
    color: colors.muted,
    fontSize: 14,
    lineHeight: 20,
  },
  transactionRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: 12,
    minHeight: 62,
  },
  transactionIcon: {
    alignItems: "center",
    backgroundColor: "#eaf5ef",
    borderRadius: 14,
    height: 42,
    justifyContent: "center",
    width: 42,
  },
  insightStats: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  metricPill: {
    backgroundColor: colors.softSurface,
    borderRadius: 14,
    minWidth: "22%",
    padding: 10,
  },
  metricPillValue: {
    color: colors.text,
    fontSize: 18,
    fontWeight: "900",
  },
  metricPillLabel: {
    color: colors.muted,
    fontSize: 11,
    fontWeight: "700",
    marginTop: 2,
  },
  anomalyLine: {
    flexDirection: "row",
    gap: 10,
  },
  anomalyDot: {
    backgroundColor: colors.amber,
    borderRadius: 5,
    height: 10,
    marginTop: 8,
    width: 10,
  },
  anomalyLabel: {
    color: colors.secondary,
    fontSize: 13,
    fontWeight: "800",
  },
  anomalyCopy: {
    color: colors.text,
    fontSize: 15,
    lineHeight: 21,
    marginTop: 2,
  },
  emptyState: {
    alignItems: "flex-start",
    backgroundColor: colors.surface,
    borderColor: "#e6e8e2",
    borderRadius: 28,
    borderWidth: 1,
    gap: 14,
    padding: 22,
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
    fontSize: 23,
    fontWeight: "900",
  },
  emptyCopy: {
    color: colors.muted,
    fontSize: 16,
    lineHeight: 23,
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
  skeletonStack: {
    gap: 18,
  },
  skeleton: {
    backgroundColor: "#eceee8",
    borderRadius: 24,
  },
  skeletonHero: {
    height: 216,
  },
  skeletonInsight: {
    height: 112,
  },
  skeletonMetric: {
    height: 94,
    width: "47%",
  },
  errorPanel: {
    backgroundColor: "#fff8ec",
    borderColor: "#efc37b",
    borderRadius: 22,
    borderWidth: 1,
    gap: 12,
    padding: 18,
  },
  errorTitle: {
    color: colors.text,
    fontSize: 16,
    fontWeight: "800",
  },
  pressed: {
    opacity: 0.72,
  },
});
