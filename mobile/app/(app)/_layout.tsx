import { Ionicons } from "@expo/vector-icons";
import { Redirect, Tabs } from "expo-router";
import { ActivityIndicator, StyleSheet, View } from "react-native";

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
        headerStyle: { backgroundColor: "#F7F4EF" },
        headerTitleStyle: { color: "#111816" },
        tabBarActiveTintColor: "#256B5B",
        tabBarInactiveTintColor: "#7A736C",
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Dashboard",
          tabBarIcon: ({ color, size }) => <Ionicons color={color} name="home-outline" size={size} />,
        }}
      />
      <Tabs.Screen
        name="import"
        options={{
          title: "Import",
          tabBarIcon: ({ color, size }) => <Ionicons color={color} name="add-circle-outline" size={size} />,
        }}
      />
      <Tabs.Screen
        name="transactions"
        options={{
          title: "Transactions",
          tabBarIcon: ({ color, size }) => <Ionicons color={color} name="list-outline" size={size} />,
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
        name="budget-leaks"
        options={{
          title: "Budget Leaks",
          tabBarIcon: ({ color, size }) => <Ionicons color={color} name="analytics-outline" size={size} />,
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: "Settings",
          tabBarIcon: ({ color, size }) => <Ionicons color={color} name="settings-outline" size={size} />,
        }}
      />
      <Tabs.Screen name="add-transaction" options={{ href: null, title: "Add transaction" }} />
      <Tabs.Screen name="paste-import" options={{ href: null, title: "Paste transactions" }} />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  centered: {
    alignItems: "center",
    backgroundColor: "#F7F4EF",
    flex: 1,
    justifyContent: "center",
  },
});
