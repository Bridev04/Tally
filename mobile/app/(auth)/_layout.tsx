import { Redirect, Stack } from "expo-router";
import { ActivityIndicator, StyleSheet, View } from "react-native";

import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { colors as defaultColors } from "@/theme";

export default function AuthLayout() {
  const { isLoading, token } = useAuth();
  const { colors } = useTheme();

  if (isLoading) {
    return (
      <View style={[styles.centered, { backgroundColor: colors.background }]}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }

  if (token) {
    return <Redirect href="/(app)" />;
  }

  return <Stack screenOptions={{ contentStyle: { backgroundColor: colors.background }, headerShown: false }} />;
}

const styles = StyleSheet.create({
  centered: {
    alignItems: "center",
    backgroundColor: defaultColors.background,
    flex: 1,
    justifyContent: "center",
  },
});
