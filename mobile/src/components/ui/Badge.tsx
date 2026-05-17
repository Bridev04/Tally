import { StyleSheet, Text, View } from "react-native";

import { colors, radius } from "@/theme";

type BadgeProps = {
  label: string;
  tone?: "neutral" | "success" | "caution" | "danger" | "info";
};

export function Badge({ label, tone = "neutral" }: BadgeProps) {
  return (
    <View style={[styles.badge, styles[tone]]}>
      <Text style={[styles.text, styles[`${tone}Text`]]}>{label}</Text>
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
