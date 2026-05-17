import { Ionicons } from "@expo/vector-icons";
import { useEffect, useMemo, useState } from "react";
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
  clearDemoData,
  deleteAccount,
  deleteAppData,
  exportUserData,
  getPrivacySummary,
  type PrivacySummary,
} from "@/lib/api";
import { colors, radius, typography } from "@/theme";

const deleteDataPhrase = "DELETE MY TALLY DATA";
const deleteAccountPhrase = "DELETE MY ACCOUNT";

type ConfirmMode = "clear-demo" | "delete-data" | "delete-account" | null;

export default function SettingsScreen() {
  const { logout, token, user } = useAuth();
  const [summary, setSummary] = useState<PrivacySummary | null>(null);
  const [isLoadingSummary, setIsLoadingSummary] = useState(true);
  const [summaryMessage, setSummaryMessage] = useState<string | null>(null);
  const [exportPreview, setExportPreview] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [confirmMode, setConfirmMode] = useState<ConfirmMode>(null);
  const [confirmationText, setConfirmationText] = useState("");

  const requiredPhrase = confirmMode === "delete-data" ? deleteDataPhrase : deleteAccountPhrase;
  const confirmEnabled = confirmMode === "clear-demo" || confirmationText === requiredPhrase;
  const isBusy = activeAction !== null;

  const sourceLabels = useMemo(() => {
    if (!summary) {
      return [];
    }
    const sources = [];
    if (summary.data_sources_used.csv_upload) sources.push("CSV upload");
    if (summary.data_sources_used.manual_entry) sources.push("Manual entry");
    if (summary.data_sources_used.paste_import) sources.push("Paste import");
    if (summary.data_sources_used.demo_data) sources.push("Demo data");
    return sources.length ? sources : ["No transaction data yet"];
  }, [summary]);

  async function refreshSummary() {
    if (!token) {
      return;
    }
    setIsLoadingSummary(true);
    setSummaryMessage(null);
    try {
      const nextSummary = await getPrivacySummary(token);
      setSummary(nextSummary);
    } catch {
      setSummaryMessage("We couldn't load your privacy summary. Please try again.");
    } finally {
      setIsLoadingSummary(false);
    }
  }

  useEffect(() => {
    refreshSummary();
  }, [token]);

  function openConfirm(mode: ConfirmMode) {
    setStatusMessage(null);
    setConfirmationText("");
    setConfirmMode(mode);
  }

  function closeConfirm() {
    if (!isBusy) {
      setConfirmMode(null);
      setConfirmationText("");
    }
  }

  async function handleExport() {
    if (!token || isBusy) {
      return;
    }
    setActiveAction("export");
    setStatusMessage(null);
    try {
      const exported = await exportUserData(token);
      setExportPreview(JSON.stringify(exported, null, 2));
      setStatusMessage("Your Tally data export is ready as a JSON preview.");
    } catch {
      setStatusMessage("We couldn't export your data. Please try again.");
    } finally {
      setActiveAction(null);
    }
  }

  async function handleConfirmAction() {
    if (!token || !confirmMode || isBusy || !confirmEnabled) {
      return;
    }
    setActiveAction(confirmMode);
    setStatusMessage(null);
    try {
      if (confirmMode === "clear-demo") {
        await clearDemoData(token);
        setStatusMessage("Demo data cleared.");
        setConfirmMode(null);
        await refreshSummary();
      }
      if (confirmMode === "delete-data") {
        await deleteAppData(token, confirmationText);
        setStatusMessage("Your imported Tally data was deleted. Your account remains active.");
        setExportPreview(null);
        setConfirmMode(null);
        await refreshSummary();
      }
      if (confirmMode === "delete-account") {
        await deleteAccount(token, confirmationText);
        setConfirmMode(null);
        await logout();
      }
    } catch {
      const fallbackDeleteMessage =
        confirmMode === "clear-demo"
          ? "We couldn't clear demo data. Please try again."
          : confirmMode === "delete-account"
            ? "We couldn't delete your account. Please try again."
            : "We couldn't delete your data. Please try again.";
      setStatusMessage(
        confirmationText && confirmationText !== requiredPhrase
          ? "Confirmation text does not match."
          : fallbackDeleteMessage,
      );
    } finally {
      setActiveAction(null);
    }
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.header}>
          <View>
            <Text style={styles.kicker}>Profile</Text>
            <Text style={styles.title}>Settings</Text>
          </View>
          <Pressable accessibilityRole="button" onPress={logout} style={styles.logoutButton}>
            <Ionicons color={colors.primary} name="log-out-outline" size={18} />
            <Text style={styles.logoutText}>Log out</Text>
          </Pressable>
        </View>

        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Account</Text>
          <Text style={styles.label}>Email</Text>
          <Text style={styles.value}>{user?.email}</Text>
          <Text style={styles.label}>App version</Text>
          <Text style={styles.value}>0.1.0</Text>
        </View>

        <View style={styles.card}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Privacy & Data</Text>
            {isLoadingSummary ? <ActivityIndicator color={colors.primary} size="small" /> : null}
          </View>
          <Text style={styles.note}>Tally does not connect to your bank.</Text>
          <Text style={styles.bodyText}>Your insights are based only on imported/manual/demo transactions.</Text>
          {summaryMessage ? <Text style={styles.errorText}>{summaryMessage}</Text> : null}
          {summary ? (
            <>
              <View style={styles.statsGrid}>
                <Metric label="Transactions" value={summary.transaction_count} />
                <Metric label="Uploads" value={summary.upload_count} />
                <Metric label="Recurring" value={summary.subscription_count} />
                <Metric label="Budget leaks" value={summary.anomaly_count} />
                <Metric label="Reports" value={summary.monthly_report_count} />
              </View>
              <View style={styles.sourceRow}>
                {sourceLabels.map((source) => (
                  <View key={source} style={styles.sourcePill}>
                    <Text style={styles.sourceText}>{source}</Text>
                  </View>
                ))}
              </View>
            </>
          ) : null}
        </View>

        <ActionCard
          description="Download a JSON copy of the data stored in your Tally account."
          icon="download-outline"
          isLoading={activeAction === "export"}
          onPress={handleExport}
          title="Export Data"
          buttonText="Export my Tally data"
        />

        {exportPreview ? (
          <View style={styles.previewCard}>
            <Text style={styles.sectionTitle}>JSON Preview</Text>
            <ScrollView style={styles.previewBox}>
              <Text selectable style={styles.previewText}>
                {exportPreview}
              </Text>
            </ScrollView>
          </View>
        ) : null}

        <ActionCard
          buttonText="Clear demo data"
          description="Remove synthetic sample transactions while keeping your account."
          icon="sparkles-outline"
          isLoading={activeAction === "clear-demo"}
          onPress={() => openConfirm("clear-demo")}
          title="Clear Demo Data"
        />

        <ActionCard
          buttonText="Delete app data"
          description="Delete your imported transactions, subscriptions, budget leaks, and reports while keeping your account."
          destructive
          icon="trash-outline"
          isLoading={activeAction === "delete-data"}
          onPress={() => openConfirm("delete-data")}
          title="Delete Imported Data"
        />

        <ActionCard
          buttonText="Delete account"
          description="Delete your Tally account and associated app data."
          destructive
          icon="person-remove-outline"
          isLoading={activeAction === "delete-account"}
          onPress={() => openConfirm("delete-account")}
          title="Delete Account"
        />

        {statusMessage ? <Text style={styles.statusText}>{statusMessage}</Text> : null}
      </ScrollView>

      <Modal animationType="fade" onRequestClose={closeConfirm} transparent visible={confirmMode !== null}>
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>{modalTitle(confirmMode)}</Text>
            <Text style={styles.modalBody}>{modalBody(confirmMode)}</Text>
            {confirmMode !== "clear-demo" ? (
              <View style={styles.confirmBlock}>
                <Text style={styles.confirmLabel}>Type {requiredPhrase} to confirm.</Text>
                <TextInput
                  autoCapitalize="characters"
                  editable={!isBusy}
                  onChangeText={setConfirmationText}
                  placeholder={requiredPhrase}
                  placeholderTextColor={colors.textMuted}
                  style={styles.confirmInput}
                  value={confirmationText}
                />
              </View>
            ) : null}
            <View style={styles.modalActions}>
              <Pressable accessibilityRole="button" disabled={isBusy} onPress={closeConfirm} style={styles.cancelButton}>
                <Text style={styles.cancelText}>Cancel</Text>
              </Pressable>
              <Pressable
                accessibilityRole="button"
                disabled={!confirmEnabled || isBusy}
                onPress={handleConfirmAction}
                style={[styles.confirmButton, (!confirmEnabled || isBusy) && styles.disabledButton]}
              >
                {isBusy ? <ActivityIndicator color={colors.white} /> : <Text style={styles.confirmText}>{modalConfirmText(confirmMode)}</Text>}
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricValue}>{value}</Text>
      <Text style={styles.metricLabel}>{label}</Text>
    </View>
  );
}

function ActionCard({
  buttonText,
  description,
  destructive = false,
  icon,
  isLoading,
  onPress,
  title,
}: {
  buttonText: string;
  description: string;
  destructive?: boolean;
  icon: keyof typeof Ionicons.glyphMap;
  isLoading: boolean;
  onPress: () => void;
  title: string;
}) {
  return (
    <View style={styles.card}>
      <View style={styles.actionTitleRow}>
        <View style={[styles.iconBadge, destructive && styles.destructiveIconBadge]}>
          <Ionicons color={destructive ? colors.danger : colors.primary} name={icon} size={18} />
        </View>
        <Text style={styles.sectionTitle}>{title}</Text>
      </View>
      <Text style={styles.bodyText}>{description}</Text>
      <Pressable
        accessibilityRole="button"
        disabled={isLoading}
        onPress={onPress}
        style={[styles.primaryButton, destructive && styles.destructiveButton, isLoading && styles.disabledButton]}
      >
        {isLoading ? <ActivityIndicator color={colors.white} /> : <Text style={styles.primaryButtonText}>{buttonText}</Text>}
      </Pressable>
    </View>
  );
}

function modalTitle(mode: ConfirmMode) {
  if (mode === "clear-demo") return "Clear demo data?";
  if (mode === "delete-data") return "Delete app data?";
  if (mode === "delete-account") return "Delete account?";
  return "";
}

function modalBody(mode: ConfirmMode) {
  if (mode === "clear-demo") {
    return "This removes sample data loaded for demos. Your account will remain.";
  }
  if (mode === "delete-data") {
    return "This deletes imported transactions, recurring payment detections, budget leaks, and monthly reports. Your account will remain.";
  }
  if (mode === "delete-account") {
    return "Deleting your account removes your Tally profile and associated app data.";
  }
  return "";
}

function modalConfirmText(mode: ConfirmMode) {
  if (mode === "clear-demo") return "Clear demo data";
  if (mode === "delete-data") return "Delete app data";
  if (mode === "delete-account") return "Delete account";
  return "Confirm";
}

const styles = StyleSheet.create({
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  content: {
    gap: 16,
    padding: 20,
    paddingBottom: 112,
  },
  header: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  kicker: {
    color: colors.textSecondary,
    fontSize: 13,
    fontWeight: "700",
    textTransform: "uppercase",
  },
  title: {
    color: colors.text,
    ...typography.title,
    marginTop: 4,
  },
  logoutButton: {
    alignItems: "center",
    backgroundColor: colors.surfaceRaised,
    borderColor: colors.borderStrong,
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: "row",
    gap: 6,
    minHeight: 42,
    paddingHorizontal: 12,
  },
  logoutText: {
    color: colors.primary,
    fontSize: 14,
    fontWeight: "800",
  },
  card: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.xl,
    borderWidth: 1,
    gap: 12,
    padding: 16,
  },
  previewCard: {
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radius.xl,
    borderWidth: 1,
    gap: 12,
    padding: 16,
  },
  sectionHeader: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  sectionTitle: {
    color: colors.text,
    fontSize: 18,
    fontWeight: "800",
  },
  label: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: "800",
    textTransform: "uppercase",
  },
  value: {
    color: colors.text,
    fontSize: 16,
    fontWeight: "700",
  },
  note: {
    color: colors.primary,
    fontSize: 16,
    fontWeight: "800",
  },
  bodyText: {
    color: colors.textSecondary,
    fontSize: 14,
    lineHeight: 20,
  },
  errorText: {
    color: colors.danger,
    fontSize: 14,
    fontWeight: "700",
  },
  statsGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  metric: {
    backgroundColor: colors.surfaceRaised,
    borderRadius: radius.md,
    minWidth: 96,
    padding: 12,
  },
  metricValue: {
    color: colors.primary,
    fontSize: 20,
    fontWeight: "900",
  },
  metricLabel: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: "700",
    marginTop: 4,
  },
  sourceRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  sourcePill: {
    backgroundColor: colors.glow,
    borderRadius: radius.md,
    paddingHorizontal: 10,
    paddingVertical: 7,
  },
  sourceText: {
    color: colors.primary,
    fontSize: 12,
    fontWeight: "800",
  },
  actionTitleRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: 10,
  },
  iconBadge: {
    alignItems: "center",
    backgroundColor: colors.glow,
    borderRadius: radius.md,
    height: 34,
    justifyContent: "center",
    width: 34,
  },
  destructiveIconBadge: {
    backgroundColor: "rgba(255, 95, 87, 0.12)",
  },
  primaryButton: {
    alignItems: "center",
    backgroundColor: colors.primaryStrong,
    borderRadius: radius.lg,
    justifyContent: "center",
    minHeight: 48,
  },
  destructiveButton: {
    backgroundColor: colors.danger,
  },
  primaryButtonText: {
    color: colors.white,
    fontSize: 15,
    fontWeight: "800",
  },
  disabledButton: {
    opacity: 0.45,
  },
  previewBox: {
    backgroundColor: colors.backgroundRaised,
    borderRadius: radius.md,
    maxHeight: 260,
    padding: 12,
  },
  previewText: {
    color: colors.text,
    fontFamily: "Courier",
    fontSize: 12,
    lineHeight: 17,
  },
  statusText: {
    color: colors.primary,
    fontSize: 14,
    fontWeight: "800",
    textAlign: "center",
  },
  modalBackdrop: {
    alignItems: "center",
    backgroundColor: "rgba(0, 0, 0, 0.64)",
    flex: 1,
    justifyContent: "center",
    padding: 20,
  },
  modalCard: {
    backgroundColor: colors.elevated,
    borderColor: colors.borderStrong,
    borderRadius: radius.xl,
    borderWidth: 1,
    gap: 14,
    padding: 18,
    width: "100%",
  },
  modalTitle: {
    color: colors.text,
    fontSize: 20,
    fontWeight: "900",
  },
  modalBody: {
    color: colors.textSecondary,
    fontSize: 15,
    lineHeight: 22,
  },
  confirmBlock: {
    gap: 8,
  },
  confirmLabel: {
    color: colors.textSecondary,
    fontSize: 13,
    fontWeight: "800",
  },
  confirmInput: {
    backgroundColor: colors.surface,
    borderColor: colors.borderStrong,
    borderRadius: radius.md,
    borderWidth: 1,
    color: colors.text,
    fontSize: 15,
    minHeight: 48,
    paddingHorizontal: 12,
  },
  modalActions: {
    flexDirection: "row",
    gap: 10,
  },
  cancelButton: {
    alignItems: "center",
    backgroundColor: colors.surfaceRaised,
    borderRadius: radius.lg,
    flex: 1,
    justifyContent: "center",
    minHeight: 48,
  },
  cancelText: {
    color: colors.primary,
    fontSize: 15,
    fontWeight: "800",
  },
  confirmButton: {
    alignItems: "center",
    backgroundColor: colors.danger,
    borderRadius: radius.lg,
    flex: 1,
    justifyContent: "center",
    minHeight: 48,
  },
  confirmText: {
    color: colors.white,
    fontSize: 15,
    fontWeight: "800",
  },
});
