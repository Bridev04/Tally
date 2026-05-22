import { AuthForm } from "@/components/AuthForm";
import { Screen } from "@/components/Screen";
import { useAuth } from "@/context/AuthContext";

export default function RegisterScreen() {
  const { register } = useAuth();

  return (
    <Screen bottomInset={false} contentStyle={{ justifyContent: "center" }}>
      <AuthForm mode="register" onSubmit={register} />
    </Screen>
  );
}
