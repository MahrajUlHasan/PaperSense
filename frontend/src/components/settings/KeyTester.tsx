"use client";

import { CircleCheck, LoaderCircle, TriangleAlert } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import type { ProviderId } from "@/lib/types";

type Result = { status: "idle" } | { status: "testing" } | { status: "ok" | "failed"; message: string };

/**
 * Sends one tiny request with the key. Give it a `key` that changes with provider, key and
 * model (see SettingsDialog), so an old result never shows next to a new key.
 */
export function KeyTester({ provider, apiKey, model }: { provider: ProviderId; apiKey: string; model: string }) {
  const [result, setResult] = useState<Result>({ status: "idle" });

  const test = async () => {
    setResult({ status: "testing" });
    try {
      const r = await api.testKey(provider, apiKey, model);
      setResult({ status: r.ok ? "ok" : "failed", message: r.message });
    } catch (error) {
      setResult({ status: "failed", message: error instanceof ApiError ? error.message : "The test couldn't run." });
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-3">
      <Button type="button" variant="secondary" onClick={test} disabled={!apiKey || result.status === "testing"}>
        {result.status === "testing" && <LoaderCircle className="animate-spin" />}
        Test key
      </Button>
      <p role="status" aria-live="polite" className="flex items-center gap-1.5 text-sm">
        {result.status === "ok" && <CircleCheck className="text-success size-4" />}
        {result.status === "failed" && <TriangleAlert className="text-destructive size-4" />}
        {"message" in result && result.message}
      </p>
    </div>
  );
}
