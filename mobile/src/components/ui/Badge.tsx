import { StyleSheet, Text, View } from "react-native";

import { useTheme } from "@/context/ThemeContext";
import { colors, radius } from "@/theme";

type BadgeProps = {
  label: string;
  tone?: "neutral" | "success" | "caution" | "danger" | "info";
};

export function Badge({ label, tone = "neutral" }: BadgeProps) {
  const { colors: themeColors } = useTheme();
  const toneStyle =
    tone === "neutral"
      ? { backgroundColor: themeColors.surfaceRaised, borderColor: themeColors.borderStrong }
      : tone === "info"
        ? { backgroundColor: themeColors.soft, borderColor: themeColors.borderStrong }
        : tone === "success"
          ? { backgroundColor: themeColors.glow, borderColor: themeColors.primaryMuted }
          : tone === "caution"
            ? { backgroundColor: "rgba(242, 169, 59, 0.12)", borderColor: themeColors.amber }
            : { backgroundColor: "rgba(255, 95, 87, 0.12)", borderColor: themeColors.danger };
  const textColor =
    tone === "success"
      ? themeColors.primary
      : tone === "caution"
        ? themeColors.amber
        : tone === "danger"
          ? themeColors.danger
          : themeColors.textSecondary;

  return (
    <View style={[styles.badge, styles[tone], toneStyle]}>
      <Text style={[styles.text, styles[`${tone}Text`], { color: textColor }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: "flex-start",
    borderRadius: radius.sm,
    borderWidth: 1,
    justifyContent: "center",
    minHeight: 26,
    paddingHorizontal: 9,
  },
  text: {
    fontSize: 11,
    fontWeight: "900",
  },
  neutral: {
    backgroundColor: colors.surfaceRaised,
    borderColor: colors.borderStrong,
  },
  success: {
    backgroundColor: "rgba(52, 209, 120, 0.12)",
    borderColor: "rgba(52, 209, 120, 0.34)",
  },
  caution: {
    backgroundColor: "rgba(242, 169, 59, 0.12)",
    borderColor: "rgba(242, 169, 59, 0.38)",
  },
  danger: {
    backgroundColor: "rgba(255, 95, 87, 0.12)",
    borderColor: "rgba(255, 95, 87, 0.38)",
  },
  info: {
    backgroundColor: "rgba(165, 173, 168, 0.12)",
    borderColor: colors.borderStrong,
  },
  neutralText: {
    color: colors.textSecondary,
  },
  successText: {
    color: colors.primary,
  },
  cautionText: {
    color: colors.amber,
  },
  dangerText: {
    color: colors.danger,
  },
  infoText: {
    color: colors.textSecondary,
  },
});
