import { ShieldCheck, Layers, Cpu } from "lucide-react";

import { FoundationStatus } from "@/components/foundation-status";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { fetchPlatformHealth } from "@/lib/api-client";
import { getInternalApiBaseUrl, getPublicConfig } from "@/lib/env";

export const dynamic = "force-dynamic";

const ARCHITECTURE_FOUNDATION = [
  {
    title: "Modular FastAPI Monolith",
    summary:
      "Versioned /api/v1 contract with strict Pydantic settings, structured secret-redacted logs, request correlation IDs, and explicit CORS allowlists.",
    icon: Layers,
  },
  {
    title: "PostgreSQL & 9 Logical Schemas",
    summary:
      "SQLAlchemy 2 async connectivity and Alembic bootstrap separating schema ownership (nextrade_owner) from least-privilege runtime access (nextrade_app).",
    icon: ShieldCheck,
  },
  {
    title: "Redis & Celery Worker Skeleton",
    summary:
      "Authenticated Redis ephemeral cache and task coordination backing Celery worker and Beat scheduler processes for future ingestion pipelines.",
    icon: Cpu,
  },
] as const;

export default async function HomePage() {
  const publicConfig = getPublicConfig();
  const initialHealth = await fetchPlatformHealth({
    baseUrl: getInternalApiBaseUrl(),
    timeoutMs: 4000,
  });

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
          <div className="flex items-center gap-3">
            <div
              className="flex h-8 w-8 items-center justify-center rounded-md bg-slate-900 text-xs font-semibold tracking-wider text-white"
              aria-hidden="true"
            >
              NX
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold tracking-tight text-slate-950">
                  {publicConfig.appName}
                </span>
                <Badge variant="ink">Phase 1 Foundation</Badge>
              </div>
              <p className="text-xs text-slate-500">
                Multi-Market Financial Intelligence Platform
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="hidden text-slate-500 sm:inline">Target Coverage:</span>
            <Badge variant="neutral">NSE · BSE · NYSE · NASDAQ</Badge>
            <Badge variant="neutral" className="font-mono uppercase">
              {publicConfig.appEnv}
            </Badge>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">
        <section className="grid grid-cols-1 gap-8 lg:grid-cols-12 lg:items-start">
          <div className="space-y-5 lg:col-span-5">
            <div className="space-y-2.5">
              <p className="font-mono text-xs font-medium uppercase tracking-widest text-teal-800">
                Engineering Baseline
              </p>
              <h1 className="text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">
                Infrastructure and Connectivity Verified.
              </h1>
              <p className="text-sm leading-6 text-slate-600">
                Core services, health verification, environment isolation, and migration
                infrastructure are active. Equity screening, fundamentals, virtual
                portfolios, and AI-grounded analysis modules will build on this base in
                subsequent phases.
              </p>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4 text-xs leading-5 text-slate-600">
              <p className="font-semibold text-slate-900">Phase 1 Guardrails</p>
              <ul className="mt-1.5 list-disc space-y-1 pl-4">
                <li>Zero fabricated securities, prices, or synthetic financial histories.</li>
                <li>Research and decision-support only; no automated live order execution.</li>
                <li>Health status reflects live PostgreSQL and Redis probes in real time.</li>
              </ul>
            </div>
          </div>

          <div className="lg:col-span-7">
            <FoundationStatus
              apiBaseUrl={publicConfig.apiBaseUrl}
              initialResult={initialHealth}
            />
          </div>
        </section>

        <section className="mt-10" aria-labelledby="architecture-pillars-heading">
          <h2
            id="architecture-pillars-heading"
            className="text-xs font-semibold uppercase tracking-wider text-slate-500"
          >
            Verified Architecture Components
          </h2>
          <div className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-3">
            {ARCHITECTURE_FOUNDATION.map((item) => {
              const Icon = item.icon;
              return (
                <Card key={item.title}>
                  <CardContent className="space-y-2 pt-5">
                    <div className="flex items-center gap-2 text-slate-900">
                      <Icon className="h-4 w-4 text-teal-800" aria-hidden="true" />
                      <h3 className="text-sm font-semibold">{item.title}</h3>
                    </div>
                    <p className="text-xs leading-5 text-slate-600">{item.summary}</p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </section>
      </main>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-6 py-4 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between">
          <p>
            Research &amp; decision-support architecture only. Does not execute live
            trades or guarantee investment returns.
          </p>
          <p className="font-mono text-slate-400">nextrade-web · v0.1.0</p>
        </div>
      </footer>
    </div>
  );
}

