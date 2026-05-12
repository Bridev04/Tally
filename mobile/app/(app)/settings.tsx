import { Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useAuth } from "@/context/AuthContext";

export default function SettingsScreen() {
  const { logout, user } = useAuth();

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.content}>
        <View>
          <Text style={styles.title}>Settings</Text>
          <Text style={styles.email}>{user?.email}</Text>
        </View>

        <Pressable accessibilityRole="button" onPress={logout} style={styles.button}>
          <Text style={styles.buttonText}>Log out</Text>
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    backgroundColor: "#F7F4EF",
    flex: 1,
  },
  content: {
    flex: 1,
    justifyContent: "space-between",
    padding: 24,
  },
  title: {
    color: "#111816",
    fontSize: 28,
    fontWeight: "700",
  },
  email: {
    color: "#5F6A63",
    fontSize: 16,
    marginTop: 8,
  },
  button: {
    alignItems: "center",
    backgroundColor: "#256B5B",
    borderRadius: 8,
    justifyContent: "center",
    minHeight: 52,
  },
  buttonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
  },
});
