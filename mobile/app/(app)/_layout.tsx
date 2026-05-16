import { Ionicons } from "@expo/vector-icons";
import { Redirect, Tabs } from "expo-router";
import type { ReactNode } from "react";
import { ActivityIndicator, Pressable, StyleSheet, View } from "react-native";

import { useAuth } from "@/context/AuthContext";

export default function AppLayout() {
  const { isLoading, token } = useAuth();

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator color="#256B5B" />
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
        tabBarActiveTintColor: "#012d1d",
        tabBarInactiveTintColor: "#858b86",
        tabBarLabelStyle: {
          fontSize: 12,
          fontWeight: "700",
        },
        tabBarStyle: {
          backgroundColor: "rgba(250, 249, 244, 0.96)",
          borderColor: "#dfe4dc",
          borderRadius: 24,
          borderTopWidth: 1,
          bottom: 12,
          elevation: 8,
          height: 72,
          left: 12,
          paddingBottom: 10,
          paddingTop: 8,
          position: "absolute",
          right: 12,
          shadowColor: "#012d1d",
          shadowOpacity: 0.08,
          shadowRadius: 18,
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
    backgroundColor: "#F7F4EF",
    flex: 1,
    justifyContent: "center",
  },
  addTabButton: {
    alignItems: "center",
    backgroundColor: "#1b4332",
    borderRadius: 34,
    height: 68,
    justifyContent: "center",
    marginTop: -28,
    shadowColor: "#012d1d",
    shadowOpacity: 0.18,
    shadowRadius: 18,
    width: 68,
  },
  pressed: {
    opacity: 0.76,
  },
});
