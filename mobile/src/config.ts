const LOCAL_API_BASE_URL = "http://localhost:8000";

export function normalizeApiBaseUrl(value: string | undefined): string {
  const trimmed = value?.trim();

  if (!trimmed) {
    return LOCAL_API_BASE_URL;
  }

  try {
    const parsed = new URL(trimmed);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
      return LOCAL_API_BASE_URL;
    }
  } catch {
    return LOCAL_API_BASE_URL;
  }

  return trimmed.replace(/\/+$/, "");
}

export const API_BASE_URL = normalizeApiBaseUrl(process.env.EXPO_PUBLIC_API_URL);
