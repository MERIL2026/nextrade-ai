import { describe, expect, it, vi } from "vitest";

import { fetchPlatformHealth } from "@/lib/api-client";
import { getPublicConfig, normalizeBaseUrl } from "@/lib/env";

describe("env configuration", () => {
  it("normalizes trailing slashes and rejects non-HTTP URLs", () => {
    expect(normalizeBaseUrl("http://localhost:8001///", "http://localhost:8001")).toBe(
      "http://localhost:8001",
    );
    expect(() => normalizeBaseUrl("ftp://invalid-scheme", "http://localhost:8001")).toThrow(
      /Invalid API base URL/,
    );
  });

  it("provides sensible NEXTRADE AI public defaults", () => {
    const cfg = getPublicConfig();
    expect(cfg.appName).toBe("NEXTRADE AI");
    expect(cfg.apiBaseUrl).toMatch(/^https?:\/\//);
  });
});

describe("fetchPlatformHealth", () => {
  it("returns ok status for healthy 200 NEX-DOC-009 envelope", async () => {
    const mockFetch = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            status: "healthy",
            service: "nextrade-api",
            environment: "test",
            version: "0.1.0",
            dependencies: {
              postgres: { status: "healthy", latency_ms: 1.5, detail: null },
              redis: { status: "healthy", latency_ms: 0.8, detail: null },
            },
          },
          meta: {
            request_id: "web_test_req_001",
            api_version: "v1",
            as_of: "2026-11-10T10:00:00Z",
          },
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
            "X-Request-ID": "web_test_req_001",
          },
        },
      ),
    );

    const res = await fetchPlatformHealth({
      baseUrl: "http://127.0.0.1:8001",
      fetchImpl: mockFetch,
    });

    expect(res.kind).toBe("ok");
    if (res.kind === "ok") {
      expect(res.payload.dependencies.postgres.status).toBe("healthy");
      expect(res.payload.dependencies.redis.status).toBe("healthy");
      expect(res.requestId).toBe("web_test_req_001");
    }
  });

  it("surfaces degraded status when API returns HTTP 503 with unhealthy dependency", async () => {
    const mockFetch = vi.fn<typeof fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: {
            status: "unhealthy",
            service: "nextrade-api",
            environment: "test",
            version: "0.1.0",
            dependencies: {
              postgres: { status: "healthy", latency_ms: 1.2, detail: null },
              redis: {
                status: "unhealthy",
                latency_ms: null,
                detail: "Redis connection unavailable.",
              },
            },
          },
          meta: {
            request_id: "web_test_req_503",
            api_version: "v1",
            as_of: "2026-11-10T10:00:00Z",
          },
        }),
        { status: 503 },
      ),
    );

    const res = await fetchPlatformHealth({
      baseUrl: "http://127.0.0.1:8001",
      fetchImpl: mockFetch,
    });

    expect(res.kind).toBe("degraded");
    if (res.kind === "degraded") {
      expect(res.httpStatus).toBe(503);
      expect(res.payload.dependencies.redis.status).toBe("unhealthy");
      expect(res.payload.dependencies.redis.detail).toContain("Redis");
    }
  });

  it("never reports healthy when network fetch rejects", async () => {
    const mockFetch = vi.fn<typeof fetch>().mockRejectedValue(new Error("ECONNREFUSED"));
    const res = await fetchPlatformHealth({
      baseUrl: "http://127.0.0.1:8001",
      fetchImpl: mockFetch,
    });

    expect(res.kind).toBe("unreachable");
    expect(res.httpStatus).toBeNull();
  });
});

