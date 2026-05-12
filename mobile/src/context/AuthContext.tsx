import * as SecureStore from "expo-secure-store";
import { createContext, PropsWithChildren, useContext, useEffect, useMemo, useState } from "react";

import { getMe, login as loginRequest, register as registerRequest } from "@/lib/api";
import type { User } from "@/types/auth";

const tokenKey = "tally.authToken";
const secureStoreOptions: SecureStore.SecureStoreOptions = {
  keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY,
};

type AuthContextValue = {
  isLoading: boolean;
  token: string | null;
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: PropsWithChildren) {
  const [isLoading, setIsLoading] = useState(true);
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function restoreSession() {
      try {
        const storedToken = await SecureStore.getItemAsync(tokenKey, secureStoreOptions);
        if (!storedToken) {
          return;
        }
        const currentUser = await getMe(storedToken);
        if (isMounted) {
          setToken(storedToken);
          setUser(currentUser);
        }
      } catch {
        await SecureStore.deleteItemAsync(tokenKey, secureStoreOptions);
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    restoreSession();
    return () => {
      isMounted = false;
    };
  }, []);

  async function persistSession(nextToken: string, nextUser: User) {
    await SecureStore.setItemAsync(tokenKey, nextToken, secureStoreOptions);
    setToken(nextToken);
    setUser(nextUser);
  }

  async function login(email: string, password: string) {
    const response = await loginRequest({ email, password });
    await persistSession(response.access_token, response.user);
  }

  async function register(email: string, password: string) {
    const response = await registerRequest({ email, password });
    await persistSession(response.access_token, response.user);
  }

  async function logout() {
    await SecureStore.deleteItemAsync(tokenKey, secureStoreOptions);
    setToken(null);
    setUser(null);
  }

  const value = useMemo(
    () => ({ isLoading, token, user, login, register, logout }),
    [isLoading, token, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within AuthProvider.");
  }
  return context;
}
