import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useAuth } from "@/context/AuthContext";
import { detectSubscriptions, listSubscriptions, loadDemoData, Subscription } from "@/lib/api";
import { colors, radius, typography } from "@/theme";

const filters = ["all", "active", "paused", "cancelled"] as const;
type StatusFilter = (typeof filters)[number];

const statusLabels: Record<string, string> = {
  all: "All",
  active: "Active",
  paused: "Paused",
  cancelled: "Cancelled",
};

const frequencyLabels: Record<string, string> = {
  weekly: "Weekly",
  biweekly: "Every 14 days",
  monthly: "Monthly",
  yearly: "Yearly",
};

export default function RecurringScreen() {
  const { token } = useAuth();
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [status, setStatus] = useState<StatusFilter>("all");
  const [isLoading, setIsLoading] = useState(false);
  const [isDetecting, setIsDetecting] = useState(false);
  const [isDemoLoading, setIsDemoLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadRecurring = useCallback(async () => {
    if (!token) {
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const response = await listSubscriptions(token, {
        status: status === "all" ? undefined : status,
        limit: 50,
      });
      setSubscriptions(response.subscriptions);
    } catch {
      setError("We could not load recurring payments.");
    } finally {
      setIsLoading(false);
    }
  }, [status, token]);

  useEffect(() => {
    loadRecurring();
  }, [loadRecurring]);

  async function handleDetection() {
    if (!token || isDetecting) {
      return;
    }
    setIsDetecting(true);
    setError(null);
    setMessage(null);
    try {
      const response = await detectSubscriptions(token);
      setMessage(
        response.detected_count > 0
          ? `${response.detected_count} recurring patterns detected.`
          : "No new recurring patterns detected.",
      );
      await loadRecurring();
    } catch {
      setError("We could not detect recurring payments. Please try again.");
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
      await detectSubscriptions(token);
      await loadRecurring();
      setMessage("Synthetic demo data loaded.");
    } catch {
      setError("We could not load demo data. Please try again.");
    } finally {
      setIsDemoLoading(false);
    }
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.headerRow}>
          <View>
            <Text style={styles.title}>Recurring</Text>
            <Text style={styles.subtitle}>{subscriptions.length} detected patterns</Text>
          </View>
          {isLoading ? <ActivityIndicator color={colors.primary} /> : null}
        </View>

        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
          {filters.map((item) => (
            <FilterChip
              key={item}
              isSelected={status === item}
              label={statusLabels[item]}
              onPress={() => setStatus(item)}
            />
          ))}
        </ScrollView>

        <View style={styles.actions}>
          <ActionButton
            icon="repeat-outline"
            isLoading={isDetecting}
            label="Detect recurring payments"
            onPress={handleDetection}
          />
          <SecondaryButton
            icon="sparkles-outline"
            isLoading={isDemoLoading}
            label="Try demo data"
            onPress={handleDemoData}
          />
        </View>

        {error ? <Text style={styles.error}>{error}</Text> : null}
        {message ? <Text style={styles.message}>{message}</Text> : null}

        {!isLoading && subscriptions.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons color={colors.primary} name="repeat-outline" size={28} />
            <Text style={styles.emptyTitle}>No recurring payments detected yet.</Text>
            <Text style={styles.emptyCopy}>Import transactions or load demo data to find patterns.</Text>
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
            {subscriptions.map((item) => (
              <RecurringCard key={item.id} item={item} />
            ))}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function RecurringCard({ item }: { item: Subscription }) {
  return (
    <View style={styles.card}>
      <View style={styles.cardTop}>
        <View style={styles.merchantMark}>
          <Text style={styles.merchantInitial}>{item.merchant_name.slice(0, 1).toUpperCase()}</Text>
        </View>
        <View style={styles.cardTitleBlock}>
          <Text numberOfLines={1} style={styles.merchant}>
            {item.merchant_name}
          </Text>
          <Text style={styles.meta}>Detected recurring pattern</Text>
        </View>
        <Text style={styles.amount}>{formatAmount(item.average_amount)}</Text>
      </View>

      <View style={styles.badgeRow}>
        <StatusBadge status={item.status} />
        <ConfidenceBadge score={item.confidence_score} />
      </View>

      <View style={styles.detailGrid}>
        <Detail label="Frequency" value={frequencyLabels[item.frequency] ?? item.frequency} />
        <Detail label="Expected again around" value={formatDate(item.next_expected_date)} />
      </View>
    </View>
  );
}

function StatusBadge({ status }: { status: string }) {
  const isActive = status === "active";
  const isPaused = status === "paused";
  return (
    <View style={[styles.statusBadge, isActive && styles.activeBadge, isPaused && styles.pausedBadge]}>
      <Text style={[styles.statusText, isActive && styles.activeText, isPaused && styles.pausedText]}>
        {statusLabels[status] ?? status}
      </Text>
    </View>
  );
}

function ConfidenceBadge({ score }: { score: number }) {
  const rounded = Math.round(score * 100);
  const tone = score >= 0.85 ? "high" : score >= 0.72 ? "medium" : "low";
  return (
    <View style={[styles.confidenceBadge, tone === "medium" && styles.mediumConfidence]}>
      <Text style={[styles.confidenceText, tone === "medium" && styles.mediumConfidenceText]}>
        Pattern confidence {rounded}%
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

function formatAmount(amount: string) {
  const value = Number(amount);
  if (!Number.isFinite(value)) {
    return amount;
  }
  return `${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} PHP`;
}

function formatDate(value: string | null) {
  if (!value) {
    return "Not enough history";
  }
  return value;
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
    fontWeight: "700",
  },
  chipTextSelected: {
    color: colors.white,
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
  merchantMark: {
    alignItems: "center",
    backgroundColor: colors.glow,
    borderRadius: radius.lg,
    height: 52,
    justifyContent: "center",
    width: 52,
  },
  merchantInitial: {
    color: colors.primary,
    fontSize: 21,
    fontWeight: "900",
  },
  cardTitleBlock: {
    flex: 1,
    gap: 4,
  },
  merchant: {
    color: colors.text,
    fontSize: 17,
    fontWeight: "800",
  },
  meta: {
    color: colors.textSecondary,
    fontSize: 13,
  },
  amount: {
    color: colors.primary,
    flexShrink: 0,
    fontSize: 15,
    fontWeight: "800",
  },
  badgeRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  statusBadge: {
    backgroundColor: colors.surfaceRaised,
    borderColor: colors.borderStrong,
    borderRadius: radius.sm,
    borderWidth: 1,
    justifyContent: "center",
    minHeight: 28,
    paddingHorizontal: 9,
  },
  activeBadge: {
    backgroundColor: "rgba(52, 209, 120, 0.12)",
    borderColor: "rgba(52, 209, 120, 0.34)",
  },
  pausedBadge: {
    backgroundColor: "rgba(242, 169, 59, 0.12)",
    borderColor: "rgba(242, 169, 59, 0.38)",
  },
  statusText: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: "800",
  },
  activeText: {
    color: colors.primary,
  },
  pausedText: {
    color: colors.amber,
  },
  confidenceBadge: {
    backgroundColor: "rgba(52, 209, 120, 0.12)",
    borderColor: "rgba(52, 209, 120, 0.34)",
    borderRadius: radius.sm,
    borderWidth: 1,
    justifyContent: "center",
    minHeight: 28,
    paddingHorizontal: 9,
  },
  mediumConfidence: {
    backgroundColor: "rgba(242, 169, 59, 0.12)",
    borderColor: "rgba(242, 169, 59, 0.38)",
  },
  confidenceText: {
    color: colors.primary,
    fontSize: 12,
    fontWeight: "800",
  },
  mediumConfidenceText: {
    color: colors.amber,
  },
  detailGrid: {
    flexDirection: "row",
    gap: 10,
  },
  detail: {
    backgroundColor: colors.surface,
    borderRadius: radius.md,
    flex: 1,
    gap: 4,
    minHeight: 62,
    padding: 10,
  },
  detailLabel: {
    color: colors.textSecondary,
    fontSize: 12,
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
