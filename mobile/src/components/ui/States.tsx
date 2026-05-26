import { Ionicons } from "@expo/vector-icons";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import { useTheme } from "@/context/ThemeContext";
import { colors, radius, spacing, typography } from "@/theme";
import { Button } from "./Button";
import { Card } from "./Card";

type EmptyStateProps = {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  description: string;
  primaryLabel?: string;
  secondaryLabel?: string;
  onPrimaryPress?: () => void;
  onSecondaryPress?: () => void;
  primaryLoading?: boolean;
  secondaryLoading?: boolean;
};

export function EmptyState({
  description,
  icon,
  onPrimaryPress,
  onSecondaryPress,
  primaryLabel,
  primaryLoading,
  secondaryLabel,
  secondaryLoading,
  title,
}: EmptyStateProps) {
  const { colors: themeColors } = useTheme();

  return (
    <Card style={styles.stateCard}>
      <View style={[styles.iconCircle, { backgroundColor: themeColors.glow }]}>
        <Ionicons color={themeColors.primary} name={icon} size={28} />
      </View>
      <Text style={[styles.title, { color: themeColors.text }]}>{title}</Text>
      <Text style={[styles.copy, { color: themeColors.textSecondary }]}>{description}</Text>
      {primaryLabel && onPrimaryPress ? (
        <Button icon="add-circle-outline" label={primaryLabel} loading={primaryLoading} onPress={onPrimaryPress} />
      ) : null}
      {secondaryLabel && onSecondaryPress ? (
        <Button
          icon="sparkles-outline"
          label={secondaryLabel}
          loading={secondaryLoading}
          onPress={onSecondaryPress}
          variant="secondary"
        />
      ) : null}
    </Card>
  );
}

export function LoadingState({ rows = 3 }: { rows?: number }) {
  const { colors: themeColors } = useTheme();
  const skeletonStyle = {
    backgroundColor: themeColors.surfaceRaised,
    borderColor: themeColors.border,
  };

  return (
    <View style={styles.loadingStack}>
      <View style={[styles.skeleton, styles.skeletonHero, skeletonStyle]} />
      {Array.from({ length: rows }).map((_, index) => (
        <View key={index} style={[styles.skeleton, skeletonStyle]} />
      ))}
    </View>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  const { colors: themeColors } = useTheme();

  return (
    <Card variant="warning">
      <Text style={[styles.errorTitle, { color: themeColors.text }]}>{message}</Text>
      <Button icon="refresh-outline" label="Retry" onPress={onRetry} variant="secondary" />
    </Card>
  );
}

export function InlineLoading() {
  const { colors: themeColors } = useTheme();

  return <ActivityIndicator color={themeColors.primary} />;
}

const styles = StyleSheet.create({
  stateCard: {
    alignItems: "flex-start",
  },
  iconCircle: {
    alignItems: "center",
    backgroundColor: colors.glow,
    borderRadius: radius.pill,
    height: 56,
    justifyContent: "center",
    width: 56,
  },
  title: {
    color: colors.text,
    ...typography.headline,
  },
  copy: {
    color: colors.textSecondary,
    ...typography.body,
  },
  loadingStack: {
    gap: spacing.md,
  },
  skeleton: {
    backgroundColor: colors.surfaceRaised,
    borderColor: colors.border,
    borderRadius: radius.xl,
    borderWidth: 1,
    height: 96,
    opacity: 0.82,
  },
  skeletonHero: {
    height: 210,
  },
  errorTitle: {
    color: colors.text,
    fontSize: 16,
    fontWeight: "900",
    lineHeight: 23,
  },
});
