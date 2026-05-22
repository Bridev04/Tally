import { Pressable, StyleSheet, Text, View } from "react-native";

import { colors, typography } from "@/theme";

type SectionHeaderProps = {
  title: string;
  action?: string;
  onPress?: () => void;
};

export function SectionHeader({ action, onPress, title }: SectionHeaderProps) {
  return (
    <View style={styles.header}>
      <Text style={styles.title}>{title}</Text>
      {action && onPress ? (
        <Pressable accessibilityRole="button" hitSlop={10} onPress={onPress}>
          <Text style={styles.action}>{action}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
  },
  title: {
    color: colors.text,
    ...typography.section,
  },
  action: {
    color: colors.primary,
    fontSize: 12,
    fontWeight: "900",
    textTransform: "uppercase",
  },
});
