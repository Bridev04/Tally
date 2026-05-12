import { Redirect } from "expo-router";
import { ActivityIndicator, StyleSheet, View } from "react-native";

import { useAuth } from "@/context/AuthContext";

export default function Index() {
  const { isLoading, token } = useAuth();

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator color="#256B5B" />
      </View>
    );
  }

  return <Redirect href={token ? "/(app)" : "/(auth)/login"} />;
}

const styles = StyleSheet.create({
  centered: {
    alignItems: "center",
    backgroundColor: "#F7F4EF",
    flex: 1,
    justifyContent: "center",
  },
});
