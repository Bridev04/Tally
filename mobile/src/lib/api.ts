import { API_BASE_URL } from "@/config";
import type { TokenResponse, User } from "@/types/auth";

type AuthPayload = {
  email: string;
  password: string;
};

type ApiErrorPayload = {
  detail?: unknown;
};

const fallbackMessage = "Something went wrong. Please try again.";

function safeErrorMessage(payload: ApiErrorPayload, fallback = fallbackMessage): string {
  if (typeof payload.detail === "string") {
    return payload.detail;
  }
  return fallback;
}

async function request<T>(
  path: string,
  options: RequestInit,
  fallback: string = fallbackMessage,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "content-type": "application/json",
      ...options.headers,
    },
  });

  const payload = (await response.json().catch(() => ({}))) as ApiErrorPayload;

  if (!response.ok) {
    throw new Error(safeErrorMessage(payload, fallback));
  }

  return payload as T;
}

export function register(payload: AuthPayload): Promise<TokenResponse> {
  return request<TokenResponse>(
    "/auth/register",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    "Could not create your account.",
  );
}

export function login(payload: AuthPayload): Promise<TokenResponse> {
  return request<TokenResponse>(
    "/auth/login",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    "Could not sign you in.",
  );
}

export function getMe(token: string): Promise<User> {
  return request<User>(
    "/auth/me",
    {
      method: "GET",
      headers: {
        authorization: `Bearer ${token}`,
      },
    },
    "Your session expired. Please sign in again.",
  );
}
