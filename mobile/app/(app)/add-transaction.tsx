import { router } from "expo-router";
import { useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { Card, Screen } from "@/components/ui";
import { useAuth } from "@/context/AuthContext";
import { createManualTransaction } from "@/lib/api";
import { colors, radius, spacing, typography } from "@/theme";

const categories = [
  "food",
  "transportation",
  "rent",
  "subscriptions",
  "shopping",
  "entertainment",
  "utilities",
  "education",
  "health",
  "income",
  "transfer",
  "fees",
  "other",
  "needs_review",
];

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

export default function AddTransactionScreen() {
  const { token } = useAuth();
  const [merchant, setMerchant] = useState("");
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState("");
  const [currency, setCurrency] = useState("PHP");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  function validate() {
    if (!merchant.trim()) {
      return "Enter a merchant.";
    }
    if (!description.trim()) {
      return "Enter a description.";
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date.trim())) {
      return "Use a date like 2026-01-04.";
    }
    if (!/^-?\d+(\.\d{1,2})?$/.test(amount.trim()) || Number(amount) === 0) {
      return "Enter a non-zero amount.";
    }
    if (!/^[A-Za-z]{3}$/.test(currency.trim())) {
      return "Use a three-letter currency code.";
    }
    return null;
  }

  async function handleSave() {
    if (!token || isSaving) {
      return;
    }
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);
    setIsSaving(true);
    try {
      await createManualTransaction(token, {
        transaction_date: date.trim(),
        merchant: merchant.trim(),
        description: description.trim(),
        amount: amount.trim(),
        currency: currency.trim().toUpperCase(),
        ...(category.trim() ? { category: category.trim() } : {}),
      });
      router.push("/(app)/transactions");
    } catch {
      setError("We could not save that transaction. Please check the fields and try again.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Screen scroll>
        <Text style={styles.title}>Add Transaction</Text>
        <Text style={styles.subtitle}>Save one transaction without connecting a bank.</Text>
        <Card variant="elevated">
          <TextInput onChangeText={setMerchant} placeholder="Merchant" placeholderTextColor={colors.textMuted} style={styles.input} value={merchant} />
          <TextInput
            keyboardType="decimal-pad"
            onChangeText={setAmount}
            placeholder="Amount"
            placeholderTextColor={colors.textMuted}
            style={styles.input}
            value={amount}
          />
          <TextInput onChangeText={setDate} placeholder="Date YYYY-MM-DD" placeholderTextColor={colors.textMuted} style={styles.input} value={date} />
          <TextInput
            autoCapitalize="characters"
            maxLength={3}
            onChangeText={setCurrency}
            placeholder="Currency"
            placeholderTextColor={colors.textMuted}
            style={styles.input}
            value={currency}
          />
          <TextInput onChangeText={setDescription} placeholder="Description" placeholderTextColor={colors.textMuted} style={styles.input} value={description} />
          <View style={styles.pickerBlock}>
            <Text style={styles.sectionLabel}>Category optional</Text>
            <View style={styles.categoryPicker}>
              <CategoryChip isSelected={!category} label="Auto" onPress={() => setCategory("")} />
              {categories.map((item) => (
                <CategoryChip
                  key={item}
                  isSelected={category === item}
                  label={categoryLabels[item]}
                  onPress={() => setCategory(item)}
                />
              ))}
            </View>
          </View>
          {error ? <Text style={styles.error}>{error}</Text> : null}
          <Pressable
            accessibilityRole="button"
            disabled={isSaving}
            onPress={handleSave}
            style={({ pressed }) => [styles.button, (pressed || isSaving) && styles.buttonPressed]}
          >
            {isSaving ? <ActivityIndicator color={colors.white} /> : <Text style={styles.buttonText}>Save transaction</Text>}
          </Pressable>
        </Card>
    </Screen>
  );
}

function CategoryChip({ isSelected, label, onPress }: { isSelected: boolean; label: string; onPress: () => void }) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [styles.chip, isSelected && styles.chipSelected, pressed && styles.buttonPressed]}
    >
      <Text style={[styles.chipText, isSelected && styles.chipTextSelected]}>{label}</Text>
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
  },
  input: {
    backgroundColor: colors.backgroundRaised,
    borderColor: colors.borderStrong,
    borderRadius: radius.md,
    borderWidth: 1,
    color: colors.text,
    fontSize: 16,
    minHeight: 52,
    paddingHorizontal: 14,
  },
  pickerBlock: {
    gap: 10,
  },
  sectionLabel: {
    color: colors.textSecondary,
    fontSize: 14,
    fontWeight: "800",
  },
  categoryPicker: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  chip: {
    backgroundColor: colors.surfaceRaised,
    borderColor: colors.borderStrong,
    borderRadius: radius.md,
    borderWidth: 1,
    minHeight: 36,
    justifyContent: "center",
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
  error: {
    color: colors.danger,
    fontSize: 14,
  },
  button: {
    alignItems: "center",
    backgroundColor: colors.primaryStrong,
    borderRadius: radius.lg,
    justifyContent: "center",
    minHeight: 52,
  },
  buttonPressed: {
    opacity: 0.82,
  },
  buttonText: {
    color: colors.white,
    fontSize: 16,
    fontWeight: "700",
  },
});
