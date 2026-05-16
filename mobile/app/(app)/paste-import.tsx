import { router } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useAuth } from "@/context/AuthContext";
import { confirmPasteImport, PastePreview, previewPasteImport } from "@/lib/api";

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
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <View>
          <Text style={styles.title}>Paste Transactions</Text>
          <Text style={styles.subtitle}>{exampleText}</Text>
        </View>
        <TextInput
          multiline
          onChangeText={(value) => {
            setText(value);
            setPreview(null);
          }}
          placeholder="Paste transaction rows"
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
          {isWorking ? <ActivityIndicator color="#256B5B" /> : <Text style={styles.secondaryButtonText}>Preview</Text>}
        </Pressable>

        {preview ? (
          <View style={styles.preview}>
            <Text style={styles.sectionTitle}>Valid rows</Text>
            {preview.valid_rows.map((row) => (
              <View key={`valid-${row.row_number}`} style={styles.row}>
                <Text style={styles.rowTitle}>{row.merchant}</Text>
                <Text style={styles.rowText}>
                  {row.transaction_date} · {row.amount} {row.currency}
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
          </View>
        ) : null}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    backgroundColor: "#F7F4EF",
    flex: 1,
  },
  content: {
    gap: 14,
    padding: 24,
  },
  title: {
    color: "#111816",
    fontSize: 28,
    fontWeight: "700",
  },
  subtitle: {
    color: "#5F6A63",
    fontFamily: "Courier",
    fontSize: 12,
    lineHeight: 18,
    marginTop: 8,
  },
  textArea: {
    backgroundColor: "#FFFFFF",
    borderColor: "#D8D0C7",
    borderRadius: 8,
    borderWidth: 1,
    color: "#111816",
    fontSize: 16,
    minHeight: 170,
    padding: 14,
  },
  error: {
    color: "#A23B31",
    fontSize: 14,
  },
  secondaryButton: {
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderColor: "#256B5B",
    borderRadius: 8,
    borderWidth: 1,
    justifyContent: "center",
    minHeight: 52,
  },
  secondaryButtonText: {
    color: "#256B5B",
    fontSize: 16,
    fontWeight: "700",
  },
  button: {
    alignItems: "center",
    backgroundColor: "#256B5B",
    borderRadius: 8,
    justifyContent: "center",
    marginTop: 8,
    minHeight: 52,
  },
  buttonPressed: {
    opacity: 0.82,
  },
  buttonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
  },
  preview: {
    gap: 10,
  },
  sectionTitle: {
    color: "#111816",
    fontSize: 16,
    fontWeight: "700",
    marginTop: 4,
  },
  row: {
    backgroundColor: "#FFFFFF",
    borderColor: "#D8D0C7",
    borderRadius: 8,
    borderWidth: 1,
    padding: 12,
  },
  rowTitle: {
    color: "#111816",
    fontSize: 15,
    fontWeight: "700",
  },
  rowText: {
    color: "#5F6A63",
    fontSize: 14,
    marginTop: 3,
  },
});
