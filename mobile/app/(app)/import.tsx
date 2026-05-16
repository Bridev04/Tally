import { Ionicons } from "@expo/vector-icons";
import * as DocumentPicker from "expo-document-picker";
import { router } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useAuth } from "@/context/AuthContext";
import { loadDemoData, uploadCsv } from "@/lib/api";

const sampleCsv = "date,description,merchant,amount,currency\n2026-01-01,Netflix Subscription,Netflix,-549,PHP";

export default function ImportScreen() {
  const { token } = useAuth();
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isWorking, setIsWorking] = useState(false);

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
      await loadDemoData(token);
      setMessage("Synthetic sample data loaded.");
      router.push("/(app)");
    } catch {
      setError("We could not load demo data. Please try again.");
    } finally {
      setIsWorking(false);
    }
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.content}>
        <View>
          <Text style={styles.title}>Import</Text>
          <Text style={styles.subtitle}>Choose the path that fits what you have right now.</Text>
        </View>

        <View style={styles.formatBox}>
          <Text style={styles.formatTitle}>CSV format</Text>
          <Text style={styles.code}>{sampleCsv}</Text>
        </View>

        {error ? <Text style={styles.error}>{error}</Text> : null}
        {message ? <Text style={styles.message}>{message}</Text> : null}

        <View style={styles.options}>
          <OptionButton
            description="Pick a CSV from iOS Files."
            icon="document-attach-outline"
            isDisabled={isWorking}
            label="Upload CSV from Files"
            onPress={handleCsvUpload}
          />
          <OptionButton
            description="Preview rows before saving."
            icon="clipboard-outline"
            isDisabled={isWorking}
            label="Paste transactions"
            onPress={() => router.push("/(app)/paste-import")}
          />
          <OptionButton
            description="Save a single transaction."
            icon="create-outline"
            isDisabled={isWorking}
            label="Add manually"
            onPress={() => router.push("/(app)/add-transaction")}
          />
          <OptionButton
            description="Load synthetic sample data."
            icon="sparkles-outline"
            isDisabled={isWorking}
            label="Try demo data"
            onPress={handleDemoData}
          />
        </View>

        {isWorking ? <ActivityIndicator color="#256B5B" /> : null}
      </ScrollView>
    </SafeAreaView>
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
      <Ionicons color="#256B5B" name={icon} size={24} />
      <View style={styles.optionText}>
        <Text style={styles.optionLabel}>{label}</Text>
        <Text style={styles.optionDescription}>{description}</Text>
      </View>
      <Ionicons color="#7A736C" name="chevron-forward" size={20} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    backgroundColor: "#F7F4EF",
    flex: 1,
  },
  content: {
    gap: 18,
    padding: 24,
  },
  title: {
    color: "#111816",
    fontSize: 32,
    fontWeight: "700",
  },
  subtitle: {
    color: "#5F6A63",
    fontSize: 16,
    lineHeight: 23,
    marginTop: 6,
  },
  formatBox: {
    backgroundColor: "#FFFFFF",
    borderColor: "#D8D0C7",
    borderRadius: 8,
    borderWidth: 1,
    padding: 14,
  },
  formatTitle: {
    color: "#38443E",
    fontSize: 14,
    fontWeight: "700",
    marginBottom: 8,
  },
  code: {
    color: "#111816",
    fontFamily: "Courier",
    fontSize: 12,
    lineHeight: 18,
  },
  error: {
    color: "#A23B31",
    fontSize: 14,
  },
  message: {
    color: "#256B5B",
    fontSize: 14,
  },
  options: {
    gap: 12,
  },
  option: {
    alignItems: "center",
    backgroundColor: "#FFFFFF",
    borderColor: "#D8D0C7",
    borderRadius: 8,
    borderWidth: 1,
    flexDirection: "row",
    gap: 12,
    minHeight: 78,
    padding: 14,
  },
  optionPressed: {
    opacity: 0.74,
  },
  optionText: {
    flex: 1,
    gap: 3,
  },
  optionLabel: {
    color: "#111816",
    fontSize: 16,
    fontWeight: "700",
  },
  optionDescription: {
    color: "#5F6A63",
    fontSize: 14,
  },
});
