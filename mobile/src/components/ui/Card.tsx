import { PropsWithChildren } from "react";
import { StyleSheet, View, type ViewStyle } from "react-native";

import { colors, radius, shadows, spacing } from "@/theme";

type CardProps = PropsWithChildren<{
  variant?: "default" | "elevated" | "primary" | "list" | "warning" | "danger";
  glow?: boolean;
  style?: ViewStyle;
}>;

export function Card({ children, glow = false, style, variant = "default" }: CardProps) {
  return <View style={[styles.base, styles[variant], glow && styles.glow, style]}>{children}</View>;
}

const styles = StyleSheet.create({
  base: {
    borderColor: colors.border,
    borderRadius: radius.xl,
    borderWidth: 1,
    gap: spacing.md,
    padding: spacing.lg,
  },
  default: {
    backgroundColor: colors.surface,
  },
  elevated: {
    backgroundColor: colors.elevated,
    borderColor: colors.borderStrong,
    ...shadows.card,
  },
  primary: {
    backgroundColor: colors.emeraldMid,
    borderColor: "rgba(52, 209, 120, 0.22)",
    ...shadows.glow,
  },
  list: {
    backgroundColor: colors.listSurface,
  },
  warning: {
    backgroundColor: "rgba(242, 169, 59, 0.10)",
    borderColor: "rgba(242, 169, 59, 0.34)",
  },
  danger: {
    backgroundColor: "rgba(255, 95, 87, 0.10)",
    borderColor: "rgba(255, 95, 87, 0.34)",
  },
  glow: {
    shadowColor: colors.primary,
    shadowOpacity: 0.2,
    shadowRadius: 22,
    shadowOffset: { width: 0, height: 10 },
    elevation: 8,
  },
});
