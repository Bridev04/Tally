import { Link } from "expo-router";
import { useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

type AuthFormProps = {
  mode: "login" | "register";
  onSubmit: (email: string, password: string) => Promise<void>;
};

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function AuthForm({ mode, onSubmit }: AuthFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const title = mode === "login" ? "Welcome back" : "Create account";
  const buttonLabel = mode === "login" ? "Sign in" : "Register";
  const alternateHref = mode === "login" ? "/(auth)/register" : "/(auth)/login";
  const alternateText = mode === "login" ? "Create an account" : "Sign in instead";

  function validate() {
    const trimmedEmail = email.trim().toLowerCase();
    if (!emailPattern.test(trimmedEmail)) {
      return "Enter a valid email address.";
    }
    if (mode === "register" && password.length < 8) {
      return "Password must be at least 8 characters.";
    }
    if (password.length === 0) {
      return "Enter your password.";
    }
    return null;
  }

  async function handleSubmit() {
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await onSubmit(email.trim().toLowerCase(), password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.brand}>Tally</Text>
      <Text style={styles.title}>{title}</Text>

      <TextInput
        autoCapitalize="none"
        autoComplete="email"
        keyboardType="email-address"
        onChangeText={setEmail}
        placeholder="Email"
        style={styles.input}
        textContentType="emailAddress"
        value={email}
      />

      <TextInput
        autoCapitalize="none"
        onChangeText={setPassword}
        placeholder="Password"
        secureTextEntry
        style={styles.input}
        textContentType={mode === "login" ? "password" : "newPassword"}
        value={password}
      />

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <Pressable
        accessibilityRole="button"
        disabled={isSubmitting}
        onPress={handleSubmit}
        style={({ pressed }) => [
          styles.button,
          (pressed || isSubmitting) && styles.buttonPressed,
        ]}
      >
        {isSubmitting ? <ActivityIndicator color="#FFFFFF" /> : <Text style={styles.buttonText}>{buttonLabel}</Text>}
      </Pressable>

      <Link href={alternateHref} style={styles.link}>
        {alternateText}
      </Link>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: 14,
  },
  brand: {
    color: "#24352F",
    fontSize: 18,
    fontWeight: "700",
  },
  title: {
    color: "#111816",
    fontSize: 32,
    fontWeight: "700",
    marginBottom: 12,
  },
  input: {
    backgroundColor: "#FFFFFF",
    borderColor: "#D8D0C7",
    borderRadius: 8,
    borderWidth: 1,
    color: "#111816",
    fontSize: 16,
    minHeight: 52,
    paddingHorizontal: 14,
  },
  error: {
    color: "#A23B31",
    fontSize: 14,
  },
  button: {
    alignItems: "center",
    backgroundColor: "#256B5B",
    borderRadius: 8,
    justifyContent: "center",
    minHeight: 52,
  },
  buttonPressed: {
    opacity: 0.82,
  },
  buttonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
  },
  link: {
    alignSelf: "center",
    color: "#256B5B",
    fontSize: 15,
    fontWeight: "600",
    paddingVertical: 10,
  },
});
