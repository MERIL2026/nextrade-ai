import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FoundationStatus } from "@/components/foundation-status";
import * as apiClient from "@/lib/api-client";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("FoundationStatus", () => {
  it("renders operational status when API and dependencies report healthy", async () => {
    vi.spyOn(apiClient, "fetchPlatformHealth").mockResolvedValue({
      kind: "ok",
      httpStatus: 200,
      requestId: "web_req_healthy_01",
      checkedAt: "2026-11-10T10:00:00Z",
      apiBaseUrl: "http://localhost:8001",
      payload: {
        status: "healthy",
        service: "nextrade-api",
        environment: "test",
        version: "0.1.0",
        dependencies: {
          postgres: { status: "healthy", latency_ms: 2.1, detail: null },
          redis: { status: "healthy", latency_ms: 0.9, detail: null },
        },
      },
      meta: {
        request_id: "web_req_healthy_01",
        api_version: "v1",
        as_of: "2026-11-10T10:00:00Z",
      },
    });

    render(<FoundationStatus apiBaseUrl="http://localhost:8001" />);

    expect(await screen.findByText("Operational")).toBeInTheDocument();
    expect(screen.getAllByText("Healthy")).toHaveLength(3);
    expect(screen.getByText("web_req_healthy_01")).toBeInTheDocument();
  });

  it("shows degraded banner and dependency detail when Redis is unavailable", async () => {
    vi.spyOn(apiClient, "fetchPlatformHealth").mockResolvedValue({
      kind: "degraded",
      httpStatus: 503,
      requestId: "web_req_degraded_02",
      checkedAt: "2026-11-10T10:01:00Z",
      apiBaseUrl: "http://localhost:8001",
      payload: {
        status: "unhealthy",
        service: "nextrade-api",
        environment: "test",
        version: "0.1.0",
        dependencies: {
          postgres: { status: "healthy", latency_ms: 1.8, detail: null },
          redis: {
            status: "unhealthy",
            latency_ms: null,
            detail: "Redis connection unavailable.",
          },
        },
      },
      meta: {
        request_id: "web_req_degraded_02",
        api_version: "v1",
        as_of: "2026-11-10T10:01:00Z",
      },
    });

    render(<FoundationStatus apiBaseUrl="http://localhost:8001" />);

    expect(await screen.findByText("Degraded (HTTP 503)")).toBeInTheDocument();
    expect(screen.getByText("Redis connection unavailable.")).toBeInTheDocument();
  });

  it("handles unreachable backend and supports manual re-check recovery", async () => {
    const spy = vi
      .spyOn(apiClient, "fetchPlatformHealth")
      .mockResolvedValueOnce({
        kind: "unreachable",
        httpStatus: null,
        requestId: "web_req_down_01",
        checkedAt: "2026-11-10T10:02:00Z",
        apiBaseUrl: "http://localhost:8001",
        message: "Unable to reach the FastAPI gateway.",
      })
      .mockResolvedValueOnce({
        kind: "ok",
        httpStatus: 200,
        requestId: "web_req_recovered_02",
        checkedAt: "2026-11-10T10:02:05Z",
        apiBaseUrl: "http://localhost:8001",
        payload: {
          status: "healthy",
          service: "nextrade-api",
          environment: "test",
          version: "0.1.0",
          dependencies: {
            postgres: { status: "healthy", latency_ms: 1.4, detail: null },
            redis: { status: "healthy", latency_ms: 0.6, detail: null },
          },
        },
        meta: {
          request_id: "web_req_recovered_02",
          api_version: "v1",
          as_of: "2026-11-10T10:02:05Z",
        },
      });

    render(<FoundationStatus apiBaseUrl="http://localhost:8001" />);

    expect(await screen.findByText("Gateway Unreachable")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Re-check/i }));

    await waitFor(() => {
      expect(screen.getByText("Operational")).toBeInTheDocument();
    });
    expect(spy).toHaveBeenCalledTimes(2);
  });
});

