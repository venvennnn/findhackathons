"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { unsubscribeAlerts } from "@/lib/api";

function UnsubscribeInner() {
  const params = useSearchParams();
  const token = params.get("token") || "";
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">(
    token ? "loading" : "error",
  );
  const [message, setMessage] = useState(
    token ? "" : "Missing unsubscribe token. Open the link from your email.",
  );

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    unsubscribeAlerts(token)
      .then((result) => {
        if (!cancelled) {
          setMessage(result.message);
          setStatus("done");
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setMessage(err instanceof Error ? err.message : "Could not unsubscribe");
          setStatus("error");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <main className="wrap" style={{ padding: "48px 16px", maxWidth: 520 }}>
      <p style={{ color: "var(--yahoo-purple)", fontWeight: 700, margin: 0 }}>
        FindHackathons
      </p>
      <h1 style={{ fontSize: 22, margin: "8px 0 12px" }}>Weekly alerts</h1>
      {status === "loading" && <p className="fineprint">Unsubscribing…</p>}
      {status === "done" && (
        <p className="fineprint" style={{ color: "var(--ok)" }}>
          {message}
        </p>
      )}
      {status === "error" && (
        <p className="fineprint" style={{ color: "var(--accent)" }}>
          {message}
        </p>
      )}
      <p style={{ marginTop: 24 }}>
        <Link href="/">← Back to listings</Link>
      </p>
    </main>
  );
}

export default function UnsubscribePage() {
  return (
    <Suspense
      fallback={
        <main className="wrap" style={{ padding: 48 }}>
          <p className="fineprint">Loading…</p>
        </main>
      }
    >
      <UnsubscribeInner />
    </Suspense>
  );
}
