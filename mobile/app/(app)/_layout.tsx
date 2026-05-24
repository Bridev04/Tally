import { Ionicons } from "@expo/vector-icons";
import { Redirect, Tabs } from "expo-router";
import type { ReactNode } from "react";
import { ActivityIndicator, Pressable, StyleSheet, View } from "react-native";

import { useAuth } from "@/context/AuthContext";
import { colors, radius, shadows } from "@/theme";

export default function AppLayout() {
  const { isLoading, token } = useAuth();

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }

  if (!token) {
    return <Redirect href="/(auth)/login" />;
  }

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.navInactive,
        tabBarLabelStyle: {
          fontSize: 12,
          fontWeight: "700",
        },
        tabBarStyle: {
          backgroundColor: colors.navRaised,
          borderColor: colors.border,
          borderRadius: radius["2xl"],
          borderTopWidth: 1,
          bottom: 12,
          height: 72,
          left: 12,
          paddingBottom: 10,
          paddingTop: 8,
          position: "absolute",
          right: 12,
          ...shadows.card,
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Home",
          tabBarIcon: ({ color, size }) => <Ionicons color={color} name="home-outline" size={size} />,
        }}
      />
      <Tabs.Screen
        name="budget-leaks"
        options={{
          title: "Insights",
          tabBarIcon: ({ color, size }) => <Ionicons color={color} name="analytics-outline" size={size} />,
        }}
      />
      <Tabs.Screen
        name="import"
        options={{
          title: "Add",
          tabBarButton: (props) => <AddTabButton {...props} />,
          tabBarIcon: ({ color, size }) => <Ionicons color={color} name="add-outline" size={size + 12} />,
        }}
      />
      <Tabs.Screen
        name="recurring"
        options={{
          title: "Recurring",
          tabBarIcon: ({ color, size }) => <Ionicons color={color} name="repeat-outline" size={size} />,
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: "Profile",
          tabBarIcon: ({ color, size }) => <Ionicons color={color} name="person-outline" size={size} />,
        }}
      />
      <Tabs.Screen name="transactions" options={{ href: null, title: "Transactions" }} />
      <Tabs.Screen name="reports" options={{ href: null, title: "Monthly Report" }} />
      <Tabs.Screen name="add-transaction" options={{ href: null, title: "Add transaction" }} />
      <Tabs.Screen name="ai-entry" options={{ href: null, title: "AI Entry" }} />
      <Tabs.Screen name="paste-import" options={{ href: null, title: "Paste transactions" }} />
    </Tabs>
  );
}

function AddTabButton({
  accessibilityState,
  children,
  onPress,
}: {
  accessibilityState?: { selected?: boolean };
  children?: ReactNode;
  onPress?: (event: any) => void;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={accessibilityState}
      onPress={onPress}
      style={({ pressed }) => [styles.addTabButton, pressed && styles.pressed]}
    >
      {children}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  centered: {
    alignItems: "center",
    backgroundColor: colors.background,
    flex: 1,
    justifyContent: "center",
  },
  addTabButton: {
    alignItems: "center",
    backgroundColor: colors.primaryStrong,
    borderRadius: 34,
    height: 68,
    justifyContent: "center",
    marginTop: -28,
    shadowColor: colors.primary,
    shadowOpacity: 0.28,
    shadowRadius: 18,
    width: 68,
  },
  pressed: {
    opacity: 0.76,
  },
});
