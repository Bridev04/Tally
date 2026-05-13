import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useAuth } from "@/context/AuthContext";
import { CategorySummaryResponse, getCategorySummary, loadDemoData } from "@/lib/api";

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

export default function HomeScreen() {
  const { token, user } = useAuth();
  const [summary, setSummary] = useState<CategorySummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isDemoLoading, setIsDemoLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSummary = useCallback(async () => {
    if (!token) {
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      setSummary(await getCategorySummary(token));
    } catch {
      setError("We could not load your dashboard.");
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  async function handleDemoData() {
    if (!token || isDemoLoading) {
      return;
    }
    setIsDemoLoading(true);
    setError(null);
    try {
      await loadDemoData(token);
      await loadSummary();
    } catch {
      setError("We could not load demo data. Please try again.");
    } finally {
      setIsDemoLoading(false);
    }
  }

  const needsReviewCount = summary?.items.find((item) => item.category === "needs_review")?.transaction_count ?? 0;
  const currency = "PHP";
  const topCategories = summary?.items.slice(0, 5) ?? [];

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.headerRow}>
          <View>
            <Text style={styles.title}>Tally</Text>
            <Text style={styles.email}>{user?.email}</Text>
          </View>
          {isLoading ? <ActivityIndicator color="#256B5B" /> : null}
        </View>

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <View style={styles.metricsGrid}>
          <MetricCard label="Expenses" value={formatAmount(summary?.total_expenses ?? "0.00", currency)} />
          <MetricCard label="Income" value={formatAmount(summary?.total_income ?? "0.00", currency)} />
          <MetricCard label="Transactions" value={String(summary?.transaction_count ?? 0)} />
          <MetricCard label="Needs Review" value={String(needsReviewCount)} tone={needsReviewCount > 0 ? "warning" : "normal"} />
        </View>

        {topCategories.length > 0 ? (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Categories</Text>
            {topCategories.map((item) => (
              <Pressable
                accessibilityRole="button"
                key={item.category}
                onPress={() => router.push("/(app)/transactions")}
                style={({ pressed }) => [styles.categoryRow, pressed && styles.pressed]}
              >
                <View style={styles.categoryTextBlock}>
                  <Text style={styles.categoryLabel}>{categoryLabels[item.category] ?? item.category}</Text>
                  <Text style={styles.categoryMeta}>
                    {item.transaction_count} transactions - {item.percentage_of_total_expenses}%
                  </Text>
                </View>
                <Text style={styles.categoryAmount}>{formatAmount(item.total_amount, currency)}</Text>
              </Pressable>
            ))}
          </View>
        ) : (
          <View style={styles.emptyState}>
            <Ionicons color="#256B5B" name="receipt-outline" size={28} />
            <Text style={styles.emptyTitle}>No transactions yet.</Text>
            <Text style={styles.emptyCopy}>Import rows or load synthetic demo data to see categorized spending patterns.</Text>
            <View style={styles.emptyActions}>
              <ActionButton icon="add-circle-outline" label="Import transactions" onPress={() => router.push("/(app)/import")} />
              <ActionButton icon="sparkles-outline" isLoading={isDemoLoading} label="Try demo data" onPress={handleDemoData} />
            </View>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function MetricCard({ label, value, tone = "normal" }: { label: string; value: string; tone?: "normal" | "warning" }) {
  return (
    <View style={[styles.metricCard, tone === "warning" && styles.warningCard]}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>{value}</Text>
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
      {isLoading ? <ActivityIndicator color="#FFFFFF" /> : <Ionicons color="#FFFFFF" name={icon} size={18} />}
      <Text style={styles.actionButtonText}>{label}</Text>
    </Pressable>
  );
}

function formatAmount(amount: string, currency: string) {
  const value = Math.abs(Number(amount));
  if (!Number.isFinite(value)) {
    return `${amount} ${currency}`;
  }
  return `${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${currency}`;
}

const styles = StyleSheet.create({
  safeArea: {
    backgroundColor: "#F7F4EF",
    flex: 1,
  },
  content: {
    gap: 18,
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
    fontSize: 34,
    fontWeight: "700",
  },
  email: {
    color: "#5F6A63",
    fontSize: 15,
    marginTop: 3,
  },
  error: {
    color: "#A23B31",
    fontSize: 14,
    lineHeight: 20,
  },
  metricsGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
  },
  metricCard: {
    backgroundColor: "#FFFFFF",
    borderColor: "#D8D0C7",
    borderRadius: 8,
    borderWidth: 1,
    minHeight: 86,
    padding: 14,
    width: "48%",
  },
  warningCard: {
    backgroundColor: "#FFF7EA",
    borderColor: "#E5B46D",
  },
  metricLabel: {
    color: "#5F6A63",
    fontSize: 13,
  },
  metricValue: {
    color: "#111816",
    fontSize: 20,
    fontWeight: "800",
    marginTop: 8,
  },
  section: {
    gap: 10,
  },
  sectionTitle: {
    color: "#38443E",
    fontSize: 15,
    fontWeight: "800",
  },
  categoryRow: {
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderColor: "#D8D0C7",
    borderRadius: 8,
    borderWidth: 1,
    flexDirection: "row",
    gap: 12,
    justifyContent: "space-between",
    minHeight: 72,
    padding: 14,
  },
  categoryTextBlock: {
    flex: 1,
    gap: 4,
  },
  categoryLabel: {
    color: "#111816",
    fontSize: 15,
    fontWeight: "800",
  },
  categoryMeta: {
    color: "#5F6A63",
    fontSize: 12,
  },
  categoryAmount: {
    color: "#256B5B",
    flexShrink: 0,
    fontSize: 14,
    fontWeight: "800",
  },
  emptyState: {
    alignItems: "flex-start",
    backgroundColor: "#FFFFFF",
    borderColor: "#D8D0C7",
    borderRadius: 8,
    borderWidth: 1,
    gap: 12,
    padding: 18,
  },
  emptyTitle: {
    color: "#111816",
    fontSize: 18,
    fontWeight: "800",
  },
  emptyCopy: {
    color: "#38443E",
    fontSize: 15,
    lineHeight: 22,
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
  pressed: {
    opacity: 0.72,
  },
});
