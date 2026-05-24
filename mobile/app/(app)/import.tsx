import { Ionicons } from "@expo/vector-icons";
import * as DocumentPicker from "expo-document-picker";
import { router } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";

import { Badge, Card, Screen } from "@/components/ui";
import { useAuth } from "@/context/AuthContext";
import { DemoScenario, loadDemoData, uploadCsv } from "@/lib/api";
import { colors, radius, spacing, typography } from "@/theme";

const sampleCsv = "date,description,merchant,amount,currency\n2026-01-01,Netflix Subscription,Netflix,-549,PHP";
const demoScenarios: Array<{ key: DemoScenario; label: string }> = [
  { key: "full_portfolio", label: "Full Portfolio Demo" },
  { key: "basic", label: "Basic Demo" },
  { key: "subscriptions", label: "Subscription Creep" },
  { key: "budget_leaks", label: "Budget Leaks" },
  { key: "needs_review", label: "Needs Review" },
];

export default function ImportScreen() {
  const { token } = useAuth();
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isWorking, setIsWorking] = useState(false);
  const [demoScenario, setDemoScenario] = useState<DemoScenario>("full_portfolio");

  async function handleCsvUpload() {
    if (!token || isWorking) {
      return;
    }
    setError(null);
    setMessage(null);
    const picked = await DocumentPicker.getDocumentAsync({
      type: ["text/csv", "text/comma-separated-values", "application/vnd.ms-excel"],
      copyToCacheDirectory: true,
      multiple: false,
    });
    if (picked.canceled) {
      return;
    }

    const asset = picked.assets[0];
    const formData = new FormData();
    formData.append("file", {
      uri: asset.uri,
      name: asset.name ?? "transactions.csv",
      type: asset.mimeType ?? "text/csv",
    } as unknown as Blob);

    setIsWorking(true);
    try {
      const result = await uploadCsv(token, formData);
      setMessage(`Imported ${result.processed_rows} transactions.`);
      router.push("/(app)/transactions");
    } catch {
      setError("We could not import that CSV. Check the format and try again.");
    } finally {
      setIsWorking(false);
    }
  }

  async function handleDemoData() {
    if (!token || isWorking) {
      return;
    }
    setError(null);
    setMessage(null);
    setIsWorking(true);
    try {
      await loadDemoData(token, demoScenario, true, true);
      setMessage("Demo data loaded. You can now explore your dashboard.");
      router.push("/(app)");
    } catch {
      setError("We could not load demo data. Please try again.");
    } finally {
      setIsWorking(false);
    }
  }

  return (
    <Screen scroll>
        <View>
          <Text style={styles.title}>Import</Text>
          <Text style={styles.subtitle}>Add transactions from AI Entry, files, pasted rows, manual entry, or safe synthetic demo data.</Text>
          <View style={styles.badgeRow}>
            <Badge label="No bank connection required" tone="success" />
            <Badge label="Imported data only" tone="info" />
          </View>
        </View>

        <Card variant="list">
          <Text style={styles.formatTitle}>CSV format</Text>
          <Text style={styles.code}>{sampleCsv}</Text>
        </Card>

        {error ? <Text style={styles.error}>{error}</Text> : null}
        {message ? <Text style={styles.message}>{message}</Text> : null}

        <Card variant="list">
          <View style={styles.demoCardHeader}>
            <View style={styles.optionIcon}>
              <Ionicons color={colors.primary} name="sparkles-outline" size={24} />
            </View>
            <View style={styles.optionText}>
              <Text style={styles.optionLabel}>Try demo data</Text>
              <Text style={styles.optionDescription}>Load synthetic transactions to explore Tally.</Text>
            </View>
          </View>
          <View style={styles.scenarioGrid}>
            {demoScenarios.map((item) => (
              <Pressable
                accessibilityRole="button"
                key={item.key}
                onPress={() => setDemoScenario(item.key)}
                style={[styles.scenarioChip, demoScenario === item.key && styles.scenarioChipSelected]}
              >
                <Text style={[styles.scenarioChipText, demoScenario === item.key && styles.scenarioChipTextSelected]}>
                  {item.label}
                </Text>
              </Pressable>
            ))}
          </View>
          <Pressable
            accessibilityRole="button"
            disabled={isWorking}
            onPress={handleDemoData}
            style={({ pressed }) => [styles.loadDemoButton, (pressed || isWorking) && styles.optionPressed]}
          >
            {isWorking ? <ActivityIndicator color="#ffffff" /> : <Ionicons color="#ffffff" name="sparkles-outline" size={18} />}
            <Text style={styles.loadDemoButtonText}>Load demo data</Text>
          </Pressable>
          <Text style={styles.demoNote}>Synthetic sample data. For portfolio preview only.</Text>
        </Card>

        <View style={styles.options}>
          <OptionButton
            description="Describe a transaction in plain language and review it before saving."
            icon="chatbubble-ellipses-outline"
            isDisabled={isWorking}
            label="AI Entry"
            onPress={() => router.push("./ai-entry")}
          />
          <OptionButton
            description="Upload a CSV file from iOS Files."
            icon="document-attach-outline"
            isDisabled={isWorking}
            label="Upload CSV from Files"
            onPress={handleCsvUpload}
          />
          <OptionButton
            description="Paste copied transaction rows."
            icon="clipboard-outline"
            isDisabled={isWorking}
            label="Paste transactions"
            onPress={() => router.push("/(app)/paste-import")}
          />
          <OptionButton
            description="Add one transaction manually."
            icon="create-outline"
            isDisabled={isWorking}
            label="Add manually"
            onPress={() => router.push("/(app)/add-transaction")}
          />
        </View>

        {isWorking ? <ActivityIndicator color={colors.primary} /> : null}
    </Screen>
  );
}

type OptionButtonProps = {
  description: string;
  icon: keyof typeof Ionicons.glyphMap;
  isDisabled: boolean;
  label: string;
  onPress: () => void;
};

function OptionButton({ description, icon, isDisabled, label, onPress }: OptionButtonProps) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={isDisabled}
      onPress={onPress}
      style={({ pressed }) => [styles.option, (pressed || isDisabled) && styles.optionPressed]}
    >
      <View style={styles.optionIcon}>
        <Ionicons color={colors.primary} name={icon} size={24} />
      </View>
      <View style={styles.optionText}>
        <Text style={styles.optionLabel}>{label}</Text>
        <Text style={styles.optionDescription}>{description}</Text>
      </View>
      <Ionicons color={colors.textMuted} name="chevron-forward" size={20} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  title: {
    color: colors.text,
    ...typography.title,
  },
  subtitle: {
    color: colors.textSecondary,
    ...typography.body,
    marginTop: 6,
  },
  badgeRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  formatTitle: {
    color: colors.textSecondary,
    fontSize: 14,
    fontWeight: "900",
    marginBottom: 8,
  },
  code: {
    color: colors.text,
    fontFamily: "Courier",
    fontSize: 12,
    lineHeight: 18,
  },
  error: {
    color: colors.danger,
    fontSize: 14,
  },
  message: {
    color: colors.primary,
    fontSize: 14,
  },
  options: {
    gap: 12,
  },
  demoCardHeader: {
    alignItems: "center",
    flexDirection: "row",
    gap: 12,
  },
  scenarioGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    marginTop: spacing.md,
  },
  scenarioChip: {
    backgroundColor: colors.surfaceRaised,
    borderColor: colors.border,
    borderRadius: radius.pill,
    borderWidth: 1,
    paddingHorizontal: 12,
    paddingVertical: 9,
  },
  scenarioChipSelected: {
    backgroundColor: colors.glow,
    borderColor: colors.primary,
  },
  scenarioChipText: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: "800",
  },
  scenarioChipTextSelected: {
    color: colors.primary,
  },
  loadDemoButton: {
    alignItems: "center",
    backgroundColor: colors.emeraldMid,
    borderRadius: radius.lg,
    flexDirection: "row",
    gap: 8,
    justifyContent: "center",
    marginTop: spacing.md,
    minHeight: 52,
    paddingHorizontal: 16,
  },
  loadDemoButtonText: {
    color: "#ffffff",
    fontSize: 15,
    fontWeight: "900",
  },
  demoNote: {
    color: colors.textMuted,
    fontSize: 12,
    marginTop: spacing.sm,
  },
  option: {
    alignItems: "center",
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.xl,
    borderWidth: 1,
    flexDirection: "row",
    gap: 12,
    minHeight: 86,
    padding: 16,
  },
  optionPressed: {
    opacity: 0.74,
  },
  optionIcon: {
    alignItems: "center",
    backgroundColor: colors.glow,
    borderRadius: radius.lg,
    height: 48,
    justifyContent: "center",
    width: 48,
  },
  optionText: {
    flex: 1,
    gap: 3,
  },
  optionLabel: {
    color: colors.text,
    fontSize: 16,
    fontWeight: "900",
  },
  optionDescription: {
    color: colors.textSecondary,
    fontSize: 14,
  },
});
