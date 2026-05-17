import { router } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { Card, Screen } from "@/components/ui";
import { useAuth } from "@/context/AuthContext";
import { confirmPasteImport, PastePreview, previewPasteImport } from "@/lib/api";
import { colors, radius, spacing, typography } from "@/theme";

const exampleText = "2026-01-01 Netflix Subscription Netflix -549 PHP\nJan 3 Grab -230 PHP";

export default function PasteImportScreen() {
  const { token } = useAuth();
  const [text, setText] = useState("");
  const [preview, setPreview] = useState<PastePreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isWorking, setIsWorking] = useState(false);

  async function handlePreview() {
    if (!token || isWorking) {
      return;
    }
    if (!text.trim()) {
      setError("Paste at least one transaction row.");
      return;
    }
    setIsWorking(true);
    setError(null);
    try {
      setPreview(await previewPasteImport(token, text));
    } catch {
      setError("We could not preview that text. Try fewer rows or check the format.");
    } finally {
      setIsWorking(false);
    }
  }

  async function handleConfirm() {
    if (!token || isWorking || !preview || preview.valid_rows.length === 0) {
      return;
    }
    setIsWorking(true);
    setError(null);
    try {
      await confirmPasteImport(token, text);
      router.push("/(app)/transactions");
    } catch {
      setError("We could not import those rows. Please preview again and retry.");
    } finally {
      setIsWorking(false);
    }
  }

  return (
    <Screen scroll>
      <View>
        <Text style={styles.title}>Paste Transactions</Text>
        <Text style={styles.copy}>Paste copied rows and preview them before saving.</Text>
      </View>

      <Card variant="list">
        <Text style={styles.exampleLabel}>Example</Text>
        <Text style={styles.example}>{exampleText}</Text>
      </Card>

      <TextInput
        multiline
        onChangeText={(value) => {
          setText(value);
          setPreview(null);
        }}
        placeholder="Paste transaction rows"
        placeholderTextColor={colors.textMuted}
        style={styles.textArea}
        textAlignVertical="top"
        value={text}
      />

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <Pressable
        accessibilityRole="button"
        disabled={isWorking}
        onPress={handlePreview}
        style={({ pressed }) => [styles.secondaryButton, (pressed || isWorking) && styles.buttonPressed]}
      >
        {isWorking ? <ActivityIndicator color={colors.primary} /> : <Text style={styles.secondaryButtonText}>Preview</Text>}
      </Pressable>

      {preview ? (
        <Card variant="elevated" style={styles.preview}>
          <Text style={styles.sectionTitle}>Valid rows</Text>
          {preview.valid_rows.map((row) => (
            <View key={`valid-${row.row_number}`} style={styles.row}>
              <Text style={styles.rowTitle}>{row.merchant}</Text>
              <Text style={styles.rowText}>
                {row.transaction_date} • {row.amount} {row.currency}
              </Text>
            </View>
          ))}

          <Text style={styles.sectionTitle}>Invalid rows</Text>
          {preview.invalid_rows.length === 0 ? <Text style={styles.rowText}>None</Text> : null}
          {preview.invalid_rows.map((row) => (
            <View key={`invalid-${row.row_number}`} style={styles.row}>
              <Text style={styles.rowTitle}>Row {row.row_number}</Text>
              <Text style={styles.rowText}>{row.reason}</Text>
            </View>
          ))}

          <Pressable
            accessibilityRole="button"
            disabled={isWorking || preview.valid_rows.length === 0}
            onPress={handleConfirm}
            style={({ pressed }) => [styles.button, (pressed || isWorking) && styles.buttonPressed]}
          >
            <Text style={styles.buttonText}>Confirm import</Text>
          </Pressable>
        </Card>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: {
    color: colors.text,
    ...typography.title,
  },
  copy: {
    color: colors.textSecondary,
    ...typography.body,
    marginTop: spacing.xs,
  },
  exampleLabel: {
    color: colors.primary,
    ...typography.label,
  },
  example: {
    color: colors.textSecondary,
    fontFamily: "Courier",
    fontSize: 12,
    lineHeight: 18,
  },
  textArea: {
    backgroundColor: colors.surface,
    borderColor: colors.borderStrong,
    borderRadius: radius.xl,
    borderWidth: 1,
    color: colors.text,
    fontSize: 16,
    minHeight: 170,
    padding: 14,
  },
  error: {
    color: colors.danger,
    fontSize: 14,
  },
  secondaryButton: {
    alignItems: "center",
    backgroundColor: colors.surfaceRaised,
    borderColor: colors.primary,
    borderRadius: radius.lg,
    borderWidth: 1,
    justifyContent: "center",
    minHeight: 52,
  },
  secondaryButtonText: {
    color: colors.primary,
    fontSize: 16,
    fontWeight: "800",
  },
  button: {
    alignItems: "center",
    backgroundColor: colors.primaryStrong,
    borderRadius: radius.lg,
    justifyContent: "center",
    marginTop: spacing.sm,
    minHeight: 52,
  },
  buttonPressed: {
    opacity: 0.82,
  },
  buttonText: {
    color: colors.white,
    fontSize: 16,
    fontWeight: "800",
  },
  preview: {
    gap: spacing.md,
  },
  sectionTitle: {
    color: colors.text,
    fontSize: 16,
    fontWeight: "900",
  },
  row: {
    backgroundColor: colors.listSurface,
    borderColor: colors.border,
    borderRadius: radius.md,
    borderWidth: 1,
    padding: spacing.md,
  },
  rowTitle: {
    color: colors.text,
    fontSize: 15,
    fontWeight: "800",
  },
  rowText: {
    color: colors.textSecondary,
    fontSize: 14,
    marginTop: 3,
  },
});
