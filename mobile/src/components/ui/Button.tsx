import { Ionicons } from "@expo/vector-icons";
import { ActivityIndicator, Pressable, StyleSheet, Text, type ViewStyle } from "react-native";

import { colors, radius, spacing } from "@/theme";

type ButtonProps = {
  label: string;
  onPress: () => void;
  variant?: "primary" | "secondary" | "ghost" | "destructive";
  icon?: keyof typeof Ionicons.glyphMap;
  loading?: boolean;
  disabled?: boolean;
  style?: ViewStyle;
};

export function Button({
  disabled = false,
  icon,
  label,
  loading = false,
  onPress,
  style,
  variant = "primary",
}: ButtonProps) {
  const isDisabled = disabled || loading;
  const spinnerColor = variant === "primary" || variant === "destructive" ? colors.white : colors.primary;

  return (
    <Pressable
      accessibilityRole="button"
      disabled={isDisabled}
      onPress={onPress}
      style={({ pressed }) => [
        styles.base,
        styles[variant],
        isDisabled && styles.disabled,
        pressed && !isDisabled && styles.pressed,
        style,
      ]}
    >
      {loading ? <ActivityIndicator color={spinnerColor} /> : icon ? <Ionicons color={iconColor(variant)} name={icon} size={18} /> : null}
      <Text style={[styles.label, styles[`${variant}Label`]]}>{label}</Text>
    </Pressable>
  );
}

function iconColor(variant: NonNullable<ButtonProps["variant"]>) {
  if (variant === "primary" || variant === "destructive") {
    return colors.white;
  }
  return colors.primary;
}

const styles = StyleSheet.create({
  base: {
    alignItems: "center",
    borderRadius: radius.lg,
    flexDirection: "row",
    gap: spacing.sm,
    justifyContent: "center",
    minHeight: 50,
    paddingHorizontal: spacing.lg,
  },
  primary: {
    backgroundColor: colors.primaryStrong,
    borderColor: colors.primary,
    borderWidth: 1,
    shadowColor: colors.primary,
    shadowOpacity: 0.2,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 8 },
  },
  secondary: {
    backgroundColor: colors.surfaceRaised,
    borderColor: colors.borderStrong,
    borderWidth: 1,
  },
  ghost: {
    backgroundColor: "transparent",
    borderColor: colors.border,
    borderWidth: 1,
  },
  destructive: {
    backgroundColor: colors.danger,
  },
  disabled: {
    opacity: 0.48,
  },
  pressed: {
    opacity: 0.76,
    transform: [{ scale: 0.995 }],
  },
  label: {
    fontSize: 15,
    fontWeight: "900",
  },
  primaryLabel: {
    color: colors.white,
  },
  secondaryLabel: {
    color: colors.primary,
  },
  ghostLabel: {
    color: colors.primary,
  },
  destructiveLabel: {
    color: colors.white,
  },
});
