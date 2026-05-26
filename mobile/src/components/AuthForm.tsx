import { Link } from "expo-router";
import { useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { Badge, Card } from "@/components/ui";
import { useTheme } from "@/context/ThemeContext";
import { radius, spacing, typography, type AppColors } from "@/theme";

type AuthFormProps = {
  mode: "login" | "register";
  onSubmit: (email: string, password: string) => Promise<void>;
};

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function AuthForm({ mode, onSubmit }: AuthFormProps) {
  const { colors } = useTheme();
  const styles = useMemo(() => makeStyles(colors), [colors]);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const title = mode === "login" ? "Welcome back" : "Create account";
  const buttonLabel = mode === "login" ? "Sign in" : "Register";
  const alternateHref = mode === "login" ? "/(auth)/register" : "/(auth)/login";
  const alternateText = mode === "login" ? "Create an account" : "Sign in instead";
  const helper =
    mode === "login"
      ? "Understand your imported spending data."
      : "No bank connection required. Use CSV, paste import, manual entry, or demo data.";

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
    } catch {
      setError(
        mode === "login"
          ? "We couldn't sign you in. Please check your details and try again."
          : "We couldn't create your account. Please check your details and try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <View style={styles.container}>
      <View style={styles.hero}>
        <Text style={styles.brand}>Tally</Text>
        <Text style={styles.tagline}>Spot spending patterns before they become habits.</Text>
        <Text style={styles.helper}>{helper}</Text>
        <View style={styles.badgeRow}>
          <Badge label="No bank connection required" tone="success" />
          <Badge label="Not financial advice" tone="info" />
        </View>
      </View>

      <Card variant="elevated" style={styles.formCard}>
        <Text style={styles.title}>{title}</Text>

        <View style={styles.fieldGroup}>
          <Text style={styles.label}>Email</Text>
          <TextInput
            autoCapitalize="none"
            autoComplete="email"
            keyboardType="email-address"
            onChangeText={setEmail}
            placeholder="you@example.com"
            placeholderTextColor={colors.textMuted}
            style={styles.input}
            textContentType="emailAddress"
            value={email}
          />
        </View>

        <View style={styles.fieldGroup}>
          <Text style={styles.label}>Password</Text>
          <TextInput
            autoCapitalize="none"
            onChangeText={setPassword}
            placeholder={mode === "login" ? "Enter your password" : "At least 8 characters"}
            placeholderTextColor={colors.textMuted}
            secureTextEntry
            style={styles.input}
            textContentType={mode === "login" ? "password" : "newPassword"}
            value={password}
          />
        </View>

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
          {isSubmitting ? <ActivityIndicator color={colors.white} /> : <Text style={styles.buttonText}>{buttonLabel}</Text>}
        </Pressable>

        <Link href={alternateHref} style={styles.link}>
          {alternateText}
        </Link>
      </Card>
    </View>
  );
}

function makeStyles(colors: AppColors) {
  return StyleSheet.create({
    container: {
      gap: spacing.xl,
      justifyContent: "center",
    },
    hero: {
      gap: spacing.md,
    },
    brand: {
      color: colors.primary,
      fontSize: 24,
      fontWeight: "900",
    },
    tagline: {
      color: colors.text,
      fontSize: 32,
      fontWeight: "900",
      lineHeight: 38,
    },
    helper: {
      color: colors.textSecondary,
      ...typography.body,
    },
    badgeRow: {
      flexDirection: "row",
      flexWrap: "wrap",
      gap: spacing.sm,
    },
    formCard: {
      gap: spacing.lg,
    },
    title: {
      color: colors.text,
      fontSize: 26,
      fontWeight: "900",
    },
    fieldGroup: {
      gap: spacing.sm,
    },
    label: {
      color: colors.textSecondary,
      ...typography.label,
    },
    input: {
      backgroundColor: colors.backgroundRaised,
      borderColor: colors.borderStrong,
      borderRadius: radius.md,
      borderWidth: 1,
      color: colors.text,
      fontSize: 16,
      minHeight: 52,
      paddingHorizontal: 14,
    },
    error: {
      color: colors.danger,
      fontSize: 14,
      lineHeight: 20,
    },
    button: {
      alignItems: "center",
      backgroundColor: colors.primaryStrong,
      borderRadius: radius.lg,
      justifyContent: "center",
      minHeight: 52,
    },
    buttonPressed: {
      opacity: 0.82,
    },
    buttonText: {
      color: colors.white,
      fontSize: 16,
      fontWeight: "900",
    },
    link: {
      alignSelf: "center",
      color: colors.primary,
      fontSize: 15,
      fontWeight: "800",
      paddingVertical: 10,
    },
  });
}
