import { StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useAuth } from "@/context/AuthContext";

export default function HomeScreen() {
  const { user } = useAuth();

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.content}>
        <Text style={styles.title}>Tally</Text>
        <Text style={styles.email}>{user?.email}</Text>
        <Text style={styles.copy}>Import transactions from files, pasted rows, manual entries, or synthetic sample data.</Text>
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
    gap: 8,
    justifyContent: "center",
    padding: 24,
  },
  title: {
    color: "#111816",
    fontSize: 34,
    fontWeight: "700",
  },
  email: {
    color: "#5F6A63",
    fontSize: 16,
  },
  copy: {
    color: "#38443E",
    fontSize: 16,
    lineHeight: 24,
    marginTop: 14,
  },
});
