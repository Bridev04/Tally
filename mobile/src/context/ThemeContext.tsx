import * as SecureStore from "expo-secure-store";
import { createContext, PropsWithChildren, useContext, useEffect, useMemo, useState } from "react";
import { Platform } from "react-native";

import { colorModes, type AppColors, type ColorMode } from "@/theme";

const defaultColorMode: ColorMode = "dark";
const themeKey = "tally.colorMode.v2";
const canUseSecureStore = Platform.OS !== "web";
const secureStoreOptions: SecureStore.SecureStoreOptions = {
  keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY,
};

type ThemeContextValue = {
  colors: AppColors;
  mode: ColorMode;
  setMode: (mode: ColorMode) => Promise<void>;
  toggleMode: () => Promise<void>;
};

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

export function ThemeProvider({ children }: PropsWithChildren) {
  const [mode, setModeState] = useState<ColorMode>(defaultColorMode);

  useEffect(() => {
    let isMounted = true;

    async function restoreTheme() {
      if (!canUseSecureStore) {
        return;
      }
      const stored = await SecureStore.getItemAsync(themeKey, secureStoreOptions);
      if (isMounted && (stored === "light" || stored === "dark")) {
        setModeState(stored);
      }
    }

    restoreTheme();
    return () => {
      isMounted = false;
    };
  }, []);

  async function setMode(nextMode: ColorMode) {
    setModeState(nextMode);
    if (canUseSecureStore) {
      await SecureStore.setItemAsync(themeKey, nextMode, secureStoreOptions);
    }
  }

  async function toggleMode() {
    await setMode(mode === "dark" ? "light" : "dark");
  }

  const value = useMemo(
    () => ({
      colors: colorModes[mode],
      mode,
      setMode,
      toggleMode,
    }),
    [mode],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider.");
  }
  return context;
}
