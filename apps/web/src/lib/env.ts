export type PublicAppEnv = "local" | "test" | "staging" | "production";

export interface PublicConfig {
  appName: string;
  appEnv: PublicAppEnv;
  apiBaseUrl: string;
}

const VALID_ENVS: ReadonlySet<PublicAppEnv> = new Set([
  "local",
  "test",
  "staging",
  "production",
]);

export function normalizeBaseUrl(rawUrl: string | undefined, fallback: string): string {
  const candidate = (rawUrl ?? "").trim() || fallback;
  const cleaned = candidate.replace(/\/+$/, "");
  if (!/^https?:\/\/[^/\s]+/i.test(cleaned)) {
    throw new Error(`Invalid API base URL configuration: ${candidate}`);
  }
  return cleaned;
}

export function getPublicConfig(): PublicConfig {
  const rawName = (process.env.NEXT_PUBLIC_APP_NAME ?? "").trim();
  const rawEnv = (process.env.NEXT_PUBLIC_APP_ENV ?? "local").trim().toLowerCase();
  const appEnv: PublicAppEnv = VALID_ENVS.has(rawEnv as PublicAppEnv)
    ? (rawEnv as PublicAppEnv)
    : "local";

  return {
    appName: rawName || "NEXTRADE AI",
    appEnv,
    apiBaseUrl: normalizeBaseUrl(
      process.env.NEXT_PUBLIC_API_BASE_URL,
      "http://localhost:8001",
    ),
  };
}

export function getInternalApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    return getPublicConfig().apiBaseUrl;
  }
  const serverKey = "INTERNAL_API_BASE_URL";
  return normalizeBaseUrl(process.env[serverKey], getPublicConfig().apiBaseUrl);
}

