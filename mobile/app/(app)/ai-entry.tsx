import { Ionicons } from "@expo/vector-icons";
import { router } from "expo-router";
import { useMemo, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { Badge, Button, Card, Screen } from "@/components/ui";
import { useAuth } from "@/context/AuthContext";
import { ChatTransactionDraft, confirmChatExpense, parseChatExpense } from "@/lib/api";
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

type ChatBubble = {
  role: "user" | "assistant";
  text: string;
};

export default function AIEntryScreen() {
  const { token } = useAuth();
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatBubble[]>([
    {
      role: "assistant",
      text: "Describe one transaction. This will be saved only after you confirm.",
    },
  ]);
  const [pendingContext, setPendingContext] = useState<string | null>(null);
  const [draft, setDraft] = useState<ChatTransactionDraft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isParsing, setIsParsing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const timezone = useMemo(() => {
    try {
      return Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Manila";
    } catch {
      return "Asia/Manila";
    }
  }, []);

  async function handleSend() {
    const trimmed = input.trim();
    if (!token || isParsing || !trimmed) {
      return;
    }

    const combinedMessage = pendingContext ? `${pendingContext}. ${trimmed}` : trimmed;
    setInput("");
    setError(null);
    setSuccess(null);
    setDraft(null);
    setMessages((current) => [...current, { role: "user", text: trimmed }]);
    setIsParsing(true);

    try {
      const response = await parseChatExpense(token, combinedMessage, timezone);
      setMessages((current) => [...current, { role: "assistant", text: response.reply }]);
      if (response.clarification_needed) {
        setPendingContext(combinedMessage);
        return;
      }
      setPendingContext(null);
      setDraft(response.draft);
    } catch {
      setError("I couldn't understand that transaction yet.");
      setMessages((current) => [
        ...current,
        { role: "assistant", text: "I couldn't understand that transaction yet." },
      ]);
    } finally {
      setIsParsing(false);
    }
  }

  async function handleSave() {
    if (!token || !draft || isSaving) {
      return;
    }
    const validationError = validateDraft(draft);
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);
    setSuccess(null);
    setIsSaving(true);
    try {
      await confirmChatExpense(token, draft);
      setSuccess("Transaction saved.");
      setMessages((current) => [...current, { role: "assistant", text: "Transaction saved." }]);
      setDraft(null);
      setPendingContext(null);
    } catch {
      setError("We couldn't save this transaction. Please try again.");
    } finally {
      setIsSaving(false);
    }
  }

  function updateDraft<K extends keyof ChatTransactionDraft>(key: K, value: ChatTransactionDraft[K]) {
    setDraft((current) => (current ? { ...current, [key]: value } : current));
  }

  return (
    <Screen scroll>
      <View>
        <Text style={styles.title}>AI Entry</Text>
        <Text style={styles.subtitle}>Describe a transaction. Tally will turn it into a draft for you to review.</Text>
        <View style={styles.badgeRow}>
          <Badge label="Review before saving" tone="success" />
          <Badge label="Not bank sync" tone="info" />
        </View>
      </View>

      <View style={styles.chatPanel}>
        {messages.map((message, index) => (
          <View
            key={`${message.role}-${index}`}
            style={[styles.bubble, message.role === "user" ? styles.userBubble : styles.assistantBubble]}
          >
            <Text style={[styles.bubbleText, message.role === "user" ? styles.userBubbleText : styles.assistantBubbleText]}>
              {message.text}
            </Text>
          </View>
        ))}
        {isParsing ? <ActivityIndicator color={colors.primary} /> : null}
      </View>

      <View style={styles.inputRow}>
        <TextInput
          multiline
          onChangeText={setInput}
          placeholder="I bought chicken from Jollibee for 200 pesos"
          placeholderTextColor={colors.textMuted}
          style={styles.messageInput}
          value={input}
        />
        <Pressable
          accessibilityRole="button"
          disabled={isParsing || !input.trim()}
          onPress={handleSend}
          style={({ pressed }) => [styles.sendButton, (pressed || isParsing || !input.trim()) && styles.pressed]}
        >
          <Ionicons color={colors.white} name="send" size={19} />
        </Pressable>
      </View>

      {error ? <Text style={styles.error}>{error}</Text> : null}
      {success ? (
        <View style={styles.successRow}>
          <Text style={styles.success}>{success}</Text>
          <Button label="View transaction" onPress={() => router.push("/(app)/transactions")} variant="secondary" />
        </View>
      ) : null}

      {draft ? (
        <DraftReviewCard
          draft={draft}
          isSaving={isSaving}
          onDiscard={() => {
            setDraft(null);
            setError(null);
          }}
          onSave={handleSave}
          onUpdate={updateDraft}
        />
      ) : null}
    </Screen>
  );
}

function DraftReviewCard({
  draft,
  isSaving,
  onDiscard,
  onSave,
  onUpdate,
}: {
  draft: ChatTransactionDraft;
  isSaving: boolean;
  onDiscard: () => void;
  onSave: () => void;
  onUpdate: <K extends keyof ChatTransactionDraft>(key: K, value: ChatTransactionDraft[K]) => void;
}) {
  return (
    <Card variant="elevated">
      <View style={styles.reviewHeader}>
        <View>
          <Text style={styles.reviewTitle}>Review draft</Text>
          <Text style={styles.reviewSubtitle}>This transaction is not saved yet.</Text>
        </View>
        <Badge label={`${Math.round(draft.confidence * 100)}% match`} tone="info" />
      </View>

      <View style={styles.typeRow}>
        <Segment
          isSelected={draft.transaction_type === "expense"}
          label="Expense"
          onPress={() => onUpdate("transaction_type", "expense")}
        />
        <Segment
          isSelected={draft.transaction_type === "income"}
          label="Income"
          onPress={() => onUpdate("transaction_type", "income")}
        />
      </View>

      <DraftInput label="Merchant" onChangeText={(value) => onUpdate("merchant", value)} value={draft.merchant} />
      <DraftInput
        label="Description"
        multiline
        onChangeText={(value) => onUpdate("description", value)}
        value={draft.description}
      />
      <View style={styles.twoColumn}>
        <DraftInput label="Amount" onChangeText={(value) => onUpdate("amount", value)} value={String(draft.amount)} />
        <DraftInput label="Date" onChangeText={(value) => onUpdate("transaction_date", value)} value={draft.transaction_date} />
      </View>
      <View style={styles.twoColumn}>
        <DraftInput
          label="Currency"
          maxLength={3}
          onChangeText={(value) => onUpdate("currency", value.toUpperCase())}
          value={draft.currency}
        />
        <DraftInput label="Payment type" onChangeText={(value) => onUpdate("payment_type", value)} value={draft.payment_type} />
      </View>

      <View style={styles.categoryBlock}>
        <Text style={styles.fieldLabel}>Category</Text>
        <View style={styles.categoryPicker}>
          {categories.map((item) => (
            <CategoryChip
              key={item}
              isSelected={draft.category === item}
              label={categoryLabels[item]}
              onPress={() => onUpdate("category", item)}
            />
          ))}
        </View>
      </View>

      <View style={styles.actionRow}>
        <Button disabled={isSaving} label="Discard" onPress={onDiscard} variant="ghost" />
        <Button
          disabled={isSaving}
          icon="checkmark-circle-outline"
          label="Save transaction"
          loading={isSaving}
          onPress={onSave}
          style={styles.saveButton}
        />
      </View>
    </Card>
  );
}

function DraftInput({
  label,
  maxLength,
  multiline = false,
  onChangeText,
  value,
}: {
  label: string;
  maxLength?: number;
  multiline?: boolean;
  onChangeText: (value: string) => void;
  value: string;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <TextInput
        maxLength={maxLength}
        multiline={multiline}
        onChangeText={onChangeText}
        placeholderTextColor={colors.textMuted}
        style={[styles.input, multiline && styles.multilineInput]}
        value={value}
      />
    </View>
  );
}

function Segment({ isSelected, label, onPress }: { isSelected: boolean; label: string; onPress: () => void }) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [styles.segment, isSelected && styles.segmentSelected, pressed && styles.pressed]}
    >
      <Text style={[styles.segmentText, isSelected && styles.segmentTextSelected]}>{label}</Text>
    </Pressable>
  );
}

function CategoryChip({ isSelected, label, onPress }: { isSelected: boolean; label: string; onPress: () => void }) {
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

function validateDraft(draft: ChatTransactionDraft) {
  if (!draft.merchant.trim()) {
    return "Please add a merchant.";
  }
  if (!draft.description.trim()) {
    return "Please add a description.";
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(draft.transaction_date.trim())) {
    return "Use a date like 2026-05-24.";
  }
  if (!/^-?\d+(\.\d{1,2})?$/.test(String(draft.amount).trim()) || Number(draft.amount) === 0) {
    return "Please add a valid amount.";
  }
  if (draft.transaction_type === "expense" && Number(draft.amount) >= 0) {
    return "Expense amounts need a minus sign.";
  }
  if (draft.transaction_type === "income" && Number(draft.amount) <= 0) {
    return "Income amounts need to be positive.";
  }
  if (!/^[A-Za-z]{3}$/.test(draft.currency.trim())) {
    return "Use a three-letter currency code.";
  }
  return null;
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
  chatPanel: {
    gap: spacing.md,
  },
  bubble: {
    borderRadius: radius.xl,
    maxWidth: "88%",
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  userBubble: {
    alignSelf: "flex-end",
    backgroundColor: colors.primaryStrong,
    borderTopRightRadius: radius.sm,
  },
  assistantBubble: {
    alignSelf: "flex-start",
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderTopLeftRadius: radius.sm,
    borderWidth: 1,
  },
  bubbleText: {
    fontSize: 15,
    lineHeight: 21,
  },
  userBubbleText: {
    color: colors.white,
    fontWeight: "700",
  },
  assistantBubbleText: {
    color: colors.text,
  },
  inputRow: {
    alignItems: "flex-end",
    flexDirection: "row",
    gap: spacing.sm,
  },
  messageInput: {
    backgroundColor: colors.backgroundRaised,
    borderColor: colors.borderStrong,
    borderRadius: radius.xl,
    borderWidth: 1,
    color: colors.text,
    flex: 1,
    fontSize: 16,
    minHeight: 56,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  sendButton: {
    alignItems: "center",
    backgroundColor: colors.primaryStrong,
    borderRadius: radius.pill,
    height: 56,
    justifyContent: "center",
    width: 56,
  },
  pressed: {
    opacity: 0.74,
  },
  error: {
    color: colors.danger,
    fontSize: 14,
  },
  successRow: {
    gap: spacing.md,
  },
  success: {
    color: colors.primary,
    fontSize: 14,
    fontWeight: "800",
  },
  reviewHeader: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: spacing.md,
    justifyContent: "space-between",
  },
  reviewTitle: {
    color: colors.text,
    ...typography.section,
  },
  reviewSubtitle: {
    color: colors.textSecondary,
    fontSize: 13,
    marginTop: 3,
  },
  typeRow: {
    backgroundColor: colors.backgroundRaised,
    borderRadius: radius.lg,
    flexDirection: "row",
    gap: spacing.sm,
    padding: spacing.xs,
  },
  segment: {
    alignItems: "center",
    borderRadius: radius.md,
    flex: 1,
    minHeight: 42,
    justifyContent: "center",
  },
  segmentSelected: {
    backgroundColor: colors.primaryStrong,
  },
  segmentText: {
    color: colors.textSecondary,
    fontSize: 14,
    fontWeight: "900",
  },
  segmentTextSelected: {
    color: colors.white,
  },
  field: {
    gap: spacing.xs,
  },
  fieldLabel: {
    color: colors.textSecondary,
    fontSize: 12,
    fontWeight: "900",
    textTransform: "uppercase",
  },
  input: {
    backgroundColor: colors.backgroundRaised,
    borderColor: colors.borderStrong,
    borderRadius: radius.md,
    borderWidth: 1,
    color: colors.text,
    fontSize: 15,
    minHeight: 50,
    paddingHorizontal: spacing.md,
  },
  multilineInput: {
    minHeight: 76,
    paddingTop: spacing.md,
    textAlignVertical: "top",
  },
  twoColumn: {
    flexDirection: "row",
    gap: spacing.md,
  },
  categoryBlock: {
    gap: spacing.sm,
  },
  categoryPicker: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  chip: {
    backgroundColor: colors.surfaceRaised,
    borderColor: colors.borderStrong,
    borderRadius: radius.md,
    borderWidth: 1,
    justifyContent: "center",
    minHeight: 36,
    paddingHorizontal: spacing.md,
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
  actionRow: {
    flexDirection: "row",
    gap: spacing.md,
  },
  saveButton: {
    flex: 1,
  },
});
