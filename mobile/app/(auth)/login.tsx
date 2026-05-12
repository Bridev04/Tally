import { AuthForm } from "@/components/AuthForm";
import { Screen } from "@/components/Screen";
import { useAuth } from "@/context/AuthContext";

export default function LoginScreen() {
  const { login } = useAuth();

  return (
    <Screen>
      <AuthForm mode="login" onSubmit={login} />
    </Screen>
  );
}
