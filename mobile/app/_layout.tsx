import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";

import { AuthProvider } from "@/context/AuthContext";
import { colors } from "@/theme";

export default function RootLayout() {
  return (
    <AuthProvider>
      <Stack screenOptions={{ contentStyle: { backgroundColor: colors.background }, headerShown: false }} />
      <StatusBar style="light" />
    </AuthProvider>
  );
}
