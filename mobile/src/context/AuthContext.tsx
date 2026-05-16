import * as SecureStore from "expo-secure-store";
import { createContext, PropsWithChildren, useContext, useEffect, useMemo, useState } from "react";
import { Platform } from "react-native";

import { getMe, login as loginRequest, register as registerRequest } from "@/lib/api";
import type { User } from "@/types/auth";

const tokenKey = "tally.authToken";
const secureStoreOptions: SecureStore.SecureStoreOptions = {
  keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY,
};
const canUseSecureStore = Platform.OS !== "web";

async function readStoredToken() {
  if (!canUseSecureStore) {
    return null;
  }
  return SecureStore.getItemAsync(tokenKey, secureStoreOptions);
}

async function writeStoredToken(nextToken: string) {
  if (!canUseSecureStore) {
    return;
  }
  await SecureStore.setItemAsync(tokenKey, nextToken, secureStoreOptions);
}

async function clearStoredToken() {
  if (!canUseSecureStore) {
    return;
  }
  await SecureStore.deleteItemAsync(tokenKey, secureStoreOptions);
}

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
        const storedToken = await readStoredToken();
        if (!storedToken) {
          return;
        }
        const currentUser = await getMe(storedToken);
        if (isMounted) {
          setToken(storedToken);
          setUser(currentUser);
        }
      } catch {
        await clearStoredToken();
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
    await writeStoredToken(nextToken);
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
    await clearStoredToken();
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
