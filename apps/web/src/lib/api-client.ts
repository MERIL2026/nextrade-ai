import { getPublicConfig, normalizeBaseUrl } from "@/lib/env";

export type DependencyHealthState = "healthy" | "unhealthy";

export interface DependencyHealth {
  status: DependencyHealthState;
  latency_ms: number | null;
  detail: string | null;
}

export interface HealthPayload {
  status: DependencyHealthState;
  service: string;
  environment: string;
  version: string;
  dependencies: {
    postgres: DependencyHealth;
    redis: DependencyHealth;
  };
}

export interface ResponseMeta {
  request_id: string;
  api_version: string;
  as_of: string;
}

export interface SuccessEnvelope<T> {
  data: T;
  meta: ResponseMeta;
}

export interface ErrorEnvelope {
  error: {
    code: string;
    message: string;
    details: Array<{ field: string | null; reason: string }>;
  };
  meta?: ResponseMeta;
}

export type PlatformHealthCheckResult =
  | {
      kind: "ok";
      httpStatus: number;
      requestId: string;
      checkedAt: string;
      apiBaseUrl: string;
      payload: HealthPayload;
      meta: ResponseMeta;
    }
  | {
      kind: "degraded";
      httpStatus: number;
      requestId: string;
      checkedAt: string;
      apiBaseUrl: string;
      payload: HealthPayload;
      meta: ResponseMeta;
    }
  | {
      kind: "error";
      httpStatus: number;
      requestId: string;
      checkedAt: string;
      apiBaseUrl: string;
      message: string;
      code?: string;
    }
  | {
      kind: "unreachable";
      httpStatus: null;
      requestId: string;
      checkedAt: string;
      apiBaseUrl: string;
      message: string;
    };

export interface FetchPlatformHealthOptions {
  baseUrl?: string;
  timeoutMs?: number;
  fetchImpl?: typeof fetch;
}

function generateClientRequestId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `web_${crypto.randomUUID().replaceAll("-", "").slice(0, 16)}`;
  }
  return `web_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isDependencyHealth(value: unknown): value is DependencyHealth {
  if (!isRecord(value)) return false;
  return (
    (value.status === "healthy" || value.status === "unhealthy") &&
    (value.latency_ms === undefined ||
      value.latency_ms === null ||
      typeof value.latency_ms === "number") &&
    (value.detail === undefined || value.detail === null || typeof value.detail === "string")
  );
}

function isHealthEnvelope(value: unknown): value is SuccessEnvelope<HealthPayload> {
  if (!isRecord(value)) return false;
  if (!isRecord(value.data) || !isRecord(value.meta)) return false;
  const data = value.data;
  const meta = value.meta;
  if (typeof meta.request_id !== "string" || typeof meta.as_of !== "string") return false;
  if (
    (data.status !== "healthy" && data.status !== "unhealthy") ||
    typeof data.service !== "string" ||
    !isRecord(data.dependencies)
  ) {
    return false;
  }
  return (
    isDependencyHealth(data.dependencies.postgres) &&
    isDependencyHealth(data.dependencies.redis)
  );
}

function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  if (!isRecord(value) || !isRecord(value.error)) return false;
  return typeof value.error.code === "string" && typeof value.error.message === "string";
}

export async function fetchPlatformHealth(
  options: FetchPlatformHealthOptions = {},
): Promise<PlatformHealthCheckResult> {
  const apiBaseUrl = normalizeBaseUrl(
    options.baseUrl,
    getPublicConfig().apiBaseUrl,
  );
  const timeoutMs = options.timeoutMs ?? 4500;
  const fetchFn = options.fetchImpl ?? fetch;
  const clientRequestId = generateClientRequestId();
  const checkedAt = new Date().toISOString();

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetchFn(`${apiBaseUrl}/api/v1/health`, {
      method: "GET",
      headers: {
        Accept: "application/json",
        "X-Request-ID": clientRequestId,
      },
      cache: "no-store",
      signal: controller.signal,
    });

    const responseRequestId = response.headers.get("X-Request-ID") ?? clientRequestId;

    let rawJson: unknown;
    try {
      rawJson = await response.json();
    } catch {
      return {
        kind: "error",
        httpStatus: response.status,
        requestId: responseRequestId,
        checkedAt,
        apiBaseUrl,
        message: `Backend returned non-JSON response (HTTP ${response.status}).`,
      };
    }

    if (isHealthEnvelope(rawJson)) {
      const normalizedPayload: HealthPayload = {
        ...rawJson.data,
        dependencies: {
          postgres: {
            status: rawJson.data.dependencies.postgres.status,
            latency_ms: rawJson.data.dependencies.postgres.latency_ms ?? null,
            detail: rawJson.data.dependencies.postgres.detail ?? null,
          },
          redis: {
            status: rawJson.data.dependencies.redis.status,
            latency_ms: rawJson.data.dependencies.redis.latency_ms ?? null,
            detail: rawJson.data.dependencies.redis.detail ?? null,
          },
        },
      };

      const isFullyHealthy =
        response.ok &&
        normalizedPayload.status === "healthy" &&
        normalizedPayload.dependencies.postgres.status === "healthy" &&
        normalizedPayload.dependencies.redis.status === "healthy";

      return {
        kind: isFullyHealthy ? "ok" : "degraded",
        httpStatus: response.status,
        requestId: rawJson.meta.request_id || responseRequestId,
        checkedAt,
        apiBaseUrl,
        payload: normalizedPayload,
        meta: rawJson.meta,
      };
    }

    if (isErrorEnvelope(rawJson)) {
      return {
        kind: "error",
        httpStatus: response.status,
        requestId: rawJson.meta?.request_id ?? responseRequestId,
        checkedAt,
        apiBaseUrl,
        code: rawJson.error.code,
        message: rawJson.error.message,
      };
    }

    return {
      kind: "error",
      httpStatus: response.status,
      requestId: responseRequestId,
      checkedAt,
      apiBaseUrl,
      message: `Unexpected health response format (HTTP ${response.status}).`,
    };
  } catch (err: unknown) {
    const isAbort = err instanceof Error && err.name === "AbortError";
    return {
      kind: "unreachable",
      httpStatus: null,
      requestId: clientRequestId,
      checkedAt,
      apiBaseUrl,
      message: isAbort
        ? `Health check timed out after ${timeoutMs} ms.`
        : "Unable to reach the FastAPI gateway. Ensure the backend service is running and CORS allows this origin.",
    };
  } finally {
    clearTimeout(timeoutId);
  }
}

