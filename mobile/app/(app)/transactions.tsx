import { useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useAuth } from "@/context/AuthContext";
import { listTransactions, Transaction } from "@/lib/api";

export default function TransactionsScreen() {
  const { token } = useAuth();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useFocusEffect(
    useCallback(() => {
      let isMounted = true;
      async function load() {
        if (!token) {
          return;
        }
        setIsLoading(true);
        setError(null);
        try {
          const response = await listTransactions(token);
          if (isMounted) {
            setTransactions(response.transactions);
          }
        } catch {
          if (isMounted) {
            setError("We could not load transactions.");
          }
        } finally {
          if (isMounted) {
            setIsLoading(false);
          }
        }
      }
      load();
      return () => {
        isMounted = false;
      };
    }, [token]),
  );

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.content}>
        <Text style={styles.title}>Transactions</Text>
        {error ? <Text style={styles.error}>{error}</Text> : null}
        {isLoading ? <ActivityIndicator color="#256B5B" /> : null}
        <FlatList
          contentContainerStyle={styles.list}
          data={transactions}
          keyExtractor={(item) => item.id}
          ListEmptyComponent={!isLoading ? <Text style={styles.empty}>No transactions yet.</Text> : null}
          renderItem={({ item }) => (
            <View style={styles.row}>
              <View style={styles.rowMain}>
                <Text style={styles.merchant}>{item.merchant_raw}</Text>
                <Text style={styles.description}>{item.description}</Text>
              </View>
              <View style={styles.amountBlock}>
                <Text style={styles.amount}>
                  {item.amount} {item.currency}
                </Text>
                <Text style={styles.date}>{item.transaction_date}</Text>
              </View>
            </View>
          )}
        />
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
    paddingHorizontal: 24,
    paddingTop: 24,
  },
  title: {
    color: "#111816",
    fontSize: 28,
    fontWeight: "700",
    marginBottom: 16,
  },
  error: {
    color: "#A23B31",
    fontSize: 14,
    marginBottom: 12,
  },
  list: {
    gap: 10,
    paddingBottom: 24,
  },
  empty: {
    color: "#5F6A63",
    fontSize: 15,
  },
  row: {
    backgroundColor: "#FFFFFF",
    borderColor: "#D8D0C7",
    borderRadius: 8,
    borderWidth: 1,
    flexDirection: "row",
    gap: 12,
    padding: 14,
  },
  rowMain: {
    flex: 1,
    gap: 4,
  },
  merchant: {
    color: "#111816",
    fontSize: 16,
    fontWeight: "700",
  },
  description: {
    color: "#5F6A63",
    fontSize: 14,
  },
  amountBlock: {
    alignItems: "flex-end",
    flexShrink: 0,
  },
  amount: {
    color: "#111816",
    fontSize: 14,
    fontWeight: "700",
  },
  date: {
    color: "#7A736C",
    fontSize: 12,
    marginTop: 4,
  },
});
