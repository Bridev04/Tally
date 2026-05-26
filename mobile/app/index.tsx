import { Redirect } from "expo-router";
import { ActivityIndicator, StyleSheet, View } from "react-native";

import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { colors as defaultColors } from "@/theme";

export default function Index() {
  const { isLoading, token } = useAuth();
  const { colors } = useTheme();

  if (isLoading) {
    return (
      <View style={[styles.centered, { backgroundColor: colors.background }]}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }

  return <Redirect href={token ? "/(app)" : "/(auth)/login"} />;
}

const styles = StyleSheet.create({
  centered: {
    alignItems: "center",
    backgroundColor: defaultColors.background,
    flex: 1,
    justifyContent: "center",
  },
});
