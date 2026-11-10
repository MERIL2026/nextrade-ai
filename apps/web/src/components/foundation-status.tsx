"use client";

import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Database,
  RefreshCw,
  Server,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  type DependencyHealth,
  fetchPlatformHealth,
  type PlatformHealthCheckResult,
} from "@/lib/api-client";

export interface FoundationStatusProps {
  apiBaseUrl: string;
  initialResult?: PlatformHealthCheckResult | null;
}

function formatLatency(dep: DependencyHealth | undefined): string {
  if (!dep) return "--";
  if (dep.latency_ms === null) return dep.status === "healthy" ? "ok" : "unavailable";
  return `${dep.latency_ms.toFixed(1)} ms`;
}

function formatUtcTimestamp(isoString: string | undefined): string {
  if (!isoString) return "--";
  const parsed = new Date(isoString);
  if (Number.isNaN(parsed.getTime())) return isoString;
  return parsed.toISOString().replace(".000", "");
}

function DependencyRow({
  label,
  role,
  icon,
  healthy,
  latencyLabel,
  detail,
}: {
  label: string;
  role: string;
  icon: React.ReactNode;
  healthy: boolean | null;
  latencyLabel: string;
  detail: string | null;
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-100 py-3 last:border-b-0 last:pb-0 first:pt-0">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-slate-200 bg-slate-50 text-slate-600">
          {icon}
        </div>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-slate-900">{label}</span>
            <span className="text-xs text-slate-500">{role}</span>
          </div>
          {detail ? (
            <p className="mt-0.5 text-xs text-rose-700">{detail}</p>
          ) : null}
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2.5">
        <span className="font-mono text-xs tabular-nums text-slate-500">
          {latencyLabel}
        </span>
        {healthy === null ? (
          <Badge variant="neutral">Checking</Badge>
        ) : healthy ? (
          <Badge variant="healthy">Healthy</Badge>
        ) : (
          <Badge variant="unhealthy">Unhealthy</Badge>
        )}
      </div>
    </div>
  );
}

export function FoundationStatus({
  apiBaseUrl,
  initialResult = null,
}: FoundationStatusProps) {
  const [result, setResult] = useState<PlatformHealthCheckResult | null>(initialResult);
  const [loading, setLoading] = useState<boolean>(initialResult === null);
  const mountedRef = useRef<boolean>(true);

  const checkHealth = useCallback(async () => {
    setLoading(true);
    const nextResult = await fetchPlatformHealth({ baseUrl: apiBaseUrl });
    if (mountedRef.current) {
      setResult(nextResult);
      setLoading(false);
    }
  }, [apiBaseUrl]);

  useEffect(() => {
    mountedRef.current = true;
    let active = true;
    void fetchPlatformHealth({ baseUrl: apiBaseUrl }).then((nextResult) => {
      if (active) {
        setResult(nextResult);
        setLoading(false);
      }
    });
    return () => {
      active = false;
      mountedRef.current = false;
    };
  }, [apiBaseUrl]);

  const apiHealthy =
    result === null
      ? null
      : result.kind === "ok" || result.kind === "degraded";
  const postgresDep =
    result && (result.kind === "ok" || result.kind === "degraded")
      ? result.payload.dependencies.postgres
      : undefined;
  const redisDep =
    result && (result.kind === "ok" || result.kind === "degraded")
      ? result.payload.dependencies.redis
      : undefined;

  let summaryBadge: React.ReactNode = <Badge variant="neutral">Checking</Badge>;
  let summaryNote = "Querying FastAPI /api/v1/health endpoint...";

  if (result?.kind === "ok") {
    summaryBadge = (
      <Badge variant="healthy">
        <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
        Operational
      </Badge>
    );
    summaryNote = "API gateway, PostgreSQL, and Redis passed live readiness probes.";
  } else if (result?.kind === "degraded") {
    summaryBadge = (
      <Badge variant="degraded">
        <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
        Degraded (HTTP {result.httpStatus})
      </Badge>
    );
    summaryNote =
      "API gateway responded, but one or more backing dependencies reported unavailable.";
  } else if (result?.kind === "error") {
    summaryBadge = (
      <Badge variant="unhealthy">
        <XCircle className="h-3.5 w-3.5" aria-hidden="true" />
        Error (HTTP {result.httpStatus})
      </Badge>
    );
    summaryNote = result.message;
  } else if (result?.kind === "unreachable") {
    summaryBadge = (
      <Badge variant="unhealthy">
        <XCircle className="h-3.5 w-3.5" aria-hidden="true" />
        Gateway Unreachable
      </Badge>
    );
    summaryNote = result.message;
  }

  return (
    <Card aria-label="Platform connectivity telemetry">
      <CardHeader className="flex-row items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold tracking-tight text-slate-900">
              System Readiness Telemetry
            </h2>
            {summaryBadge}
          </div>
          <p className="text-xs text-slate-600" role="status" aria-live="polite">
            {summaryNote}
          </p>
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={() => void checkHealth()}
          disabled={loading}
          aria-busy={loading}
        >
          <RefreshCw
            className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}
            aria-hidden="true"
          />
          {loading ? "Checking..." : "Re-check"}
        </Button>
      </CardHeader>

      <CardContent>
        <div className="divide-y divide-slate-100">
          <DependencyRow
            label="FastAPI Gateway"
            role="/api/v1/health"
            icon={<Server className="h-4 w-4" aria-hidden="true" />}
            healthy={apiHealthy}
            latencyLabel={
              result === null
                ? "..."
                : result.httpStatus !== null
                  ? `HTTP ${result.httpStatus}`
                  : "offline"
            }
            detail={
              result?.kind === "error" || result?.kind === "unreachable"
                ? result.message
                : null
            }
          />
          <DependencyRow
            label="PostgreSQL"
            role="Primary System of Record"
            icon={<Database className="h-4 w-4" aria-hidden="true" />}
            healthy={
              result === null
                ? null
                : postgresDep
                  ? postgresDep.status === "healthy"
                  : false
            }
            latencyLabel={
              result === null
                ? "..."
                : postgresDep
                  ? formatLatency(postgresDep)
                  : "unverified"
            }
            detail={postgresDep?.status === "unhealthy" ? postgresDep.detail : null}
          />
          <DependencyRow
            label="Redis"
            role="Ephemeral Cache & Queue"
            icon={<Activity className="h-4 w-4" aria-hidden="true" />}
            healthy={
              result === null
                ? null
                : redisDep
                  ? redisDep.status === "healthy"
                  : false
            }
            latencyLabel={
              result === null
                ? "..."
                : redisDep
                  ? formatLatency(redisDep)
                  : "unverified"
            }
            detail={redisDep?.status === "unhealthy" ? redisDep.detail : null}
          />
        </div>

        <dl className="mt-4 grid grid-cols-1 gap-2 rounded-md border border-slate-100 bg-slate-50/80 px-3.5 py-2.5 text-xs sm:grid-cols-3">
          <div>
            <dt className="text-slate-500">API Target</dt>
            <dd className="mt-0.5 truncate font-mono text-slate-800">{apiBaseUrl}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Request ID</dt>
            <dd className="mt-0.5 truncate font-mono text-slate-800">
              {result?.requestId ?? "--"}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Verified As Of (UTC)</dt>
            <dd className="mt-0.5 truncate font-mono tabular-nums text-slate-800">
              {result?.kind === "ok" || result?.kind === "degraded"
                ? formatUtcTimestamp(result.meta.as_of)
                : formatUtcTimestamp(result?.checkedAt)}
            </dd>
          </div>
        </dl>
      </CardContent>
    </Card>
  );
}

