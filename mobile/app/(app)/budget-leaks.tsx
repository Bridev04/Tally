import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useCallback, useEffect, useState } from "react";
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
  AnomalySummaryResponse,
  detectAnomalies,
  getAnomalies,
  getAnomalySummary,
  loadDemoData,
  SpendingAnomaly,
} from "@/lib/api";
import { colors, radius, typography } from "@/theme";

const typeLabels: Record<string, string> = {
  CATEGORY_SPIKE: "Category change",
  MERCHANT_FREQUENCY_SPIKE: "Merchant frequency",
  REPEATED_SMALL_PURCHASES: "Repeated small purchases",
  SUBSCRIPTION_PRICE_CHANGE: "Recurring charge change",
  DUPLICATE_LIKE_TRANSACTIONS: "Possible duplicate",
  NEEDS_REVIEW_CLUSTER: "Needs review",
};

const severityLabels: Record<string, string> = {
  high: "High priority",
  medium: "Medium priority",
  low: "Review",
};

const insightFilters = ["For you", "Spending", "Income", "Savings"];

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

export default function BudgetLeaksScreen() {
  const { token } = useAuth();
  const [anomalies, setAnomalies] = useState<SpendingAnomaly[]>([]);
  const [summary, setSummary] = useState<AnomalySummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isDetecting, setIsDetecting] = useState(false);
  const [isDemoLoading, setIsDemoLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadBudgetLeaks = useCallback(
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
        const [listResponse, summaryResponse] = await Promise.all([
          getAnomalies(token, { limit: 50 }),
          getAnomalySummary(token),
        ]);
        setAnomalies(listResponse.anomalies);
        setSummary(summaryResponse);
      } catch {
        setError("We could not load budget leaks.");
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [token],
  );

  useEffect(() => {
    loadBudgetLeaks();
  }, [loadBudgetLeaks]);

  async function handleDetection() {
    if (!token || isDetecting) {
      return;
    }
    setIsDetecting(true);
    setError(null);
    setMessage(null);
    try {
      const response = await detectAnomalies(token);
      setMessage(
        response.detected_count > 0
          ? `${response.detected_count} budget leaks detected from imported data.`
          : "No budget leaks detected from imported data.",
      );
      await loadBudgetLeaks();
    } catch {
      setError("We could not run detection. Please try again.");
    } finally {
      setIsDetecting(false);
    }
  }

  async function handleDemoData() {
    if (!token || isDemoLoading) {
      return;
    }
    setIsDemoLoading(true);
    setError(null);
    setMessage(null);
    try {
      await loadDemoData(token);
      await detectAnomalies(token);
      await loadBudgetLeaks();
      setMessage("Synthetic demo data loaded and reviewed.");
    } catch {
      setError("We could not load demo data. Please try again.");
    } finally {
      setIsDemoLoading(false);
    }
  }

  const needsReviewCount = anomalies.filter((item) => item.anomaly_type === "NEEDS_REVIEW_CLUSTER").length;

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl onRefresh={() => loadBudgetLeaks(true)} refreshing={isRefreshing} />}
      >
        <View style={styles.headerRow}>
          <View>
            <Text style={styles.title}>Insights</Text>
            <Text style={styles.subtitle}>
              {summary?.month ? `Detected from imported data for ${summary.month}` : "Detected from imported data only"}
            </Text>
          </View>
          {isLoading ? <ActivityIndicator color={colors.primary} /> : null}
        </View>

        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
          {insightFilters.map((item, index) => (
            <View key={item} style={[styles.chip, index === 0 && styles.chipSelected]}>
              <Text style={[styles.chipText, index === 0 && styles.chipTextSelected]}>{item}</Text>
            </View>
          ))}
        </ScrollView>

        <View style={styles.metricsGrid}>
          <MetricCard label="Total budget leaks" value={String(summary?.total_anomalies ?? anomalies.length)} />
          <MetricCard label="High priority" value={String(summary?.high_count ?? 0)} tone="high" />
          <MetricCard label="Medium priority" value={String(summary?.medium_count ?? 0)} tone="medium" />
          <MetricCard label="Needs review" value={String(needsReviewCount || summary?.low_count || 0)} tone="review" />
        </View>

        <View style={styles.actions}>
          <ActionButton icon="analytics-outline" isLoading={isDetecting} label="Run detection" onPress={handleDetection} />
          <SecondaryButton icon="sparkles-outline" isLoading={isDemoLoading} label="Try demo data" onPress={handleDemoData} />
        </View>

        {error ? <Text style={styles.error}>{error}</Text> : null}
        {message ? <Text style={styles.message}>{message}</Text> : null}

        {!isLoading && anomalies.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons color={colors.primary} name="analytics-outline" size={28} />
            <Text style={styles.emptyTitle}>No budget leaks detected yet.</Text>
            <Text style={styles.emptyCopy}>
              Import transactions or run detection to review spending patterns.
            </Text>
            <Pressable
              accessibilityRole="button"
              onPress={() => router.push("/(app)/import")}
              style={({ pressed }) => [styles.importButton, pressed && styles.pressed]}
            >
              <Ionicons color={colors.primary} name="add-circle-outline" size={18} />
              <Text style={styles.importButtonText}>Import transactions</Text>
            </Pressable>
          </View>
        ) : (
          <View style={styles.list}>
            {anomalies.map((item) => (
              <AnomalyCard item={item} key={item.id} />
            ))}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function MetricCard({
  label,
  tone = "normal",
  value,
}: {
  label: string;
  tone?: "normal" | "high" | "medium" | "review";
  value: string;
}) {
  return (
    <View style={[styles.metricCard, tone === "high" && styles.highCard, tone === "medium" && styles.mediumCard, tone === "review" && styles.reviewCard]}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{value}</Text>
    </View>
  );
}

function AnomalyCard({ item }: { item: SpendingAnomaly }) {
  const subject = item.merchant_name ?? labelForCategory(item.category ?? "needs_review");
  return (
    <View style={styles.card}>
      <View style={styles.cardTop}>
        <View style={styles.cardTitleBlock}>
          <Text style={styles.typeLabel}>{typeLabels[item.anomaly_type] ?? item.anomaly_type}</Text>
          <Text numberOfLines={1} style={styles.subject}>
            {subject}
          </Text>
        </View>
        <SeverityBadge severity={item.severity} />
      </View>

      <Text style={styles.explanation}>{item.explanation}</Text>

      <View style={styles.detailRow}>
        {item.amount_delta ? <Detail label="Change" value={formatAmount(item.amount_delta)} /> : null}
        {item.percentage_change !== null ? <Detail label="Percent" value={`${Math.round(item.percentage_change)}%`} /> : null}
        {item.transaction_count !== null ? <Detail label="Count" value={String(item.transaction_count)} /> : null}
      </View>
    </View>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  return (
    <View style={[styles.severityBadge, severity === "high" && styles.highBadge, severity === "medium" && styles.mediumBadge]}>
      <Text style={[styles.severityText, severity === "high" && styles.highText, severity === "medium" && styles.mediumText]}>
        {severityLabels[severity] ?? severity}
      </Text>
    </View>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.detail}>
      <Text style={styles.detailLabel}>{label}</Text>
      <Text style={styles.detailValue}>{value}</Text>
    </View>
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
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [styles.secondaryButton, pressed && styles.pressed]}
    >
      {isLoading ? <ActivityIndicator color={colors.primary} /> : <Ionicons color={colors.primary} name={icon} size={18} />}
      <Text style={styles.secondaryButtonText}>{label}</Text>
    </Pressable>
  );
}

function labelForCategory(category: string) {
  return categoryLabels[category] ?? category.replace("_", " ");
}

function formatAmount(amount: string) {
  const value = Number(amount);
  if (!Number.isFinite(value)) {
    return `${amount} PHP`;
  }
  const sign = value < 0 ? "-" : "";
  return `${sign}${Math.abs(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} PHP`;
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
  metricsGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
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
    justifyContent: "center",
    minHeight: 36,
    paddingHorizontal: 12,
  },
  chipSelected: {
    backgroundColor: colors.primaryStrong,
    borderColor: colors.primary,
  },
  chipText: {
    color: colors.textSecondary,
    fontSize: 13,
    fontWeight: "800",
  },
  chipTextSelected: {
    color: colors.white,
  },
  metricCard: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.lg,
    borderWidth: 1,
    minHeight: 86,
    padding: 14,
    width: "48%",
  },
  highCard: {
    backgroundColor: "rgba(255, 95, 87, 0.10)",
    borderColor: "rgba(255, 95, 87, 0.32)",
  },
  mediumCard: {
    backgroundColor: "rgba(242, 169, 59, 0.10)",
    borderColor: "rgba(242, 169, 59, 0.34)",
  },
  reviewCard: {
    backgroundColor: "rgba(52, 209, 120, 0.10)",
    borderColor: "rgba(52, 209, 120, 0.34)",
  },
  metricLabel: {
    color: colors.textSecondary,
    fontSize: 13,
  },
  metricValue: {
    color: colors.text,
    fontSize: 20,
    fontWeight: "800",
    marginTop: 8,
  },
  actions: {
    gap: 10,
  },
  actionButton: {
    alignItems: "center",
    backgroundColor: colors.primaryStrong,
    borderRadius: radius.lg,
    flexDirection: "row",
    gap: 8,
    justifyContent: "center",
    minHeight: 48,
    paddingHorizontal: 14,
  },
  actionButtonText: {
    color: colors.white,
    fontSize: 15,
    fontWeight: "800",
  },
  secondaryButton: {
    alignItems: "center",
    backgroundColor: colors.surfaceRaised,
    borderColor: colors.borderStrong,
    borderRadius: radius.lg,
    borderWidth: 1,
    flexDirection: "row",
    gap: 8,
    justifyContent: "center",
    minHeight: 46,
    paddingHorizontal: 14,
  },
  secondaryButtonText: {
    color: colors.primary,
    fontSize: 15,
    fontWeight: "800",
  },
  error: {
    color: colors.danger,
    fontSize: 14,
    lineHeight: 20,
  },
  message: {
    color: colors.primary,
    fontSize: 14,
    lineHeight: 20,
  },
  emptyState: {
    alignItems: "flex-start",
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.xl,
    borderWidth: 1,
    gap: 12,
    padding: 18,
  },
  emptyTitle: {
    color: colors.text,
    fontSize: 18,
    fontWeight: "800",
  },
  emptyCopy: {
    color: colors.textSecondary,
    fontSize: 15,
    lineHeight: 22,
  },
  importButton: {
    alignItems: "center",
    borderColor: colors.borderStrong,
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: "row",
    gap: 8,
    minHeight: 42,
    paddingHorizontal: 12,
  },
  importButtonText: {
    color: colors.primary,
    fontSize: 14,
    fontWeight: "800",
  },
  list: {
    gap: 10,
  },
  card: {
    backgroundColor: colors.listSurface,
    borderColor: colors.border,
    borderRadius: radius.xl,
    borderWidth: 1,
    gap: 12,
    padding: 14,
  },
  cardTop: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: 10,
    justifyContent: "space-between",
  },
  cardTitleBlock: {
    flex: 1,
    gap: 4,
  },
  typeLabel: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: "800",
    textTransform: "uppercase",
  },
  subject: {
    color: colors.text,
    fontSize: 17,
    fontWeight: "800",
  },
  severityBadge: {
    backgroundColor: "rgba(52, 209, 120, 0.12)",
    borderColor: "rgba(52, 209, 120, 0.34)",
    borderRadius: radius.sm,
    borderWidth: 1,
    justifyContent: "center",
    minHeight: 28,
    paddingHorizontal: 9,
  },
  highBadge: {
    backgroundColor: "rgba(255, 95, 87, 0.12)",
    borderColor: "rgba(255, 95, 87, 0.38)",
  },
  mediumBadge: {
    backgroundColor: "rgba(242, 169, 59, 0.12)",
    borderColor: "rgba(242, 169, 59, 0.38)",
  },
  severityText: {
    color: colors.primary,
    fontSize: 12,
    fontWeight: "800",
  },
  highText: {
    color: colors.danger,
  },
  mediumText: {
    color: colors.amber,
  },
  explanation: {
    color: colors.textSecondary,
    fontSize: 15,
    lineHeight: 22,
  },
  detailRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  detail: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    gap: 3,
    minWidth: 88,
    padding: 9,
  },
  detailLabel: {
    color: colors.textSecondary,
    fontSize: 11,
    fontWeight: "700",
  },
  detailValue: {
    color: colors.text,
    fontSize: 14,
    fontWeight: "800",
  },
  pressed: {
    opacity: 0.72,
  },
});
