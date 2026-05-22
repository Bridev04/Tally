import { PropsWithChildren } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, View, type StyleProp, type ViewStyle } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { colors, spacing } from "@/theme";

type ScreenProps = PropsWithChildren<{
  scroll?: boolean;
  padded?: boolean;
  bottomInset?: boolean;
  contentStyle?: StyleProp<ViewStyle>;
}>;

export function Screen({ bottomInset = true, children, contentStyle, padded = true, scroll = false }: ScreenProps) {
  const content = [styles.content, padded && styles.padded, bottomInset && styles.bottomInset, contentStyle];

  return (
    <SafeAreaView style={styles.safeArea}>
      <KeyboardAvoidingView
        behavior={Platform.select({ ios: "padding", android: undefined })}
        style={styles.keyboard}
      >
        {scroll ? (
          <ScrollView
            contentContainerStyle={content}
            keyboardShouldPersistTaps="handled"
            showsVerticalScrollIndicator={false}
          >
            {children}
          </ScrollView>
        ) : (
          <View style={content}>{children}</View>
        )}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    backgroundColor: colors.background,
    flex: 1,
  },
  keyboard: {
    flex: 1,
  },
  content: {
    flexGrow: 1,
    gap: spacing.lg,
  },
  padded: {
    padding: spacing.xl,
  },
  bottomInset: {
    paddingBottom: 116,
  },
});
