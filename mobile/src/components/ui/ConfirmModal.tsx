import { ActivityIndicator, Modal, Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { colors, radius, spacing, typography } from "@/theme";

type ConfirmModalProps = {
  visible: boolean;
  title: string;
  body: string;
  confirmLabel: string;
  requiredPhrase?: string;
  typedValue: string;
  busy?: boolean;
  onChangeText: (value: string) => void;
  onCancel: () => void;
  onConfirm: () => void;
};

export function ConfirmModal({
  body,
  busy = false,
  confirmLabel,
  onCancel,
  onChangeText,
  onConfirm,
  requiredPhrase,
  title,
  typedValue,
  visible,
}: ConfirmModalProps) {
  const enabled = !busy && (!requiredPhrase || typedValue === requiredPhrase);

  return (
    <Modal animationType="fade" onRequestClose={onCancel} transparent visible={visible}>
      <View style={styles.backdrop}>
        <View style={styles.card}>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.body}>{body}</Text>
          {requiredPhrase ? (
            <View style={styles.confirmBlock}>
              <Text style={styles.label}>Type {requiredPhrase} to confirm.</Text>
              <TextInput
                autoCapitalize="characters"
                editable={!busy}
                onChangeText={onChangeText}
                placeholder={requiredPhrase}
                placeholderTextColor={colors.textMuted}
                style={styles.input}
                value={typedValue}
              />
            </View>
          ) : null}
          <View style={styles.actions}>
            <Pressable accessibilityRole="button" disabled={busy} onPress={onCancel} style={styles.cancelButton}>
              <Text style={styles.cancelText}>Cancel</Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              disabled={!enabled}
              onPress={onConfirm}
              style={[styles.confirmButton, !enabled && styles.disabled]}
            >
              {busy ? <ActivityIndicator color={colors.white} /> : <Text style={styles.confirmText}>{confirmLabel}</Text>}
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    alignItems: "center",
    backgroundColor: "rgba(0, 0, 0, 0.64)",
    flex: 1,
    justifyContent: "center",
    padding: spacing.xl,
  },
  card: {
    backgroundColor: colors.elevated,
    borderColor: colors.borderStrong,
    borderRadius: radius.xl,
    borderWidth: 1,
    gap: spacing.md,
    padding: spacing.xl,
    width: "100%",
  },
  title: {
    color: colors.text,
    ...typography.section,
  },
  body: {
    color: colors.textSecondary,
    ...typography.body,
  },
  confirmBlock: {
    gap: spacing.sm,
  },
  label: {
    color: colors.textSecondary,
    ...typography.label,
  },
  input: {
    backgroundColor: colors.surface,
    borderColor: colors.borderStrong,
    borderRadius: radius.md,
    borderWidth: 1,
    color: colors.text,
    fontSize: 15,
    minHeight: 50,
    paddingHorizontal: spacing.md,
  },
  actions: {
    flexDirection: "row",
    gap: spacing.md,
  },
  cancelButton: {
    alignItems: "center",
    backgroundColor: colors.surfaceRaised,
    borderColor: colors.borderStrong,
    borderRadius: radius.lg,
    borderWidth: 1,
    flex: 1,
    justifyContent: "center",
    minHeight: 50,
  },
  cancelText: {
    color: colors.primary,
    fontSize: 15,
    fontWeight: "900",
  },
  confirmButton: {
    alignItems: "center",
    backgroundColor: colors.danger,
    borderRadius: radius.lg,
    flex: 1,
    justifyContent: "center",
    minHeight: 50,
  },
  confirmText: {
    color: colors.white,
    fontSize: 15,
    fontWeight: "900",
  },
  disabled: {
    opacity: 0.42,
  },
});
