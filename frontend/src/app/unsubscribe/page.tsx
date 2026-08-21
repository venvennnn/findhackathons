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
      <p style={{ fontWeight: 600, margin: 0 }}>FindHackathons</p>
      <h1 style={{ fontSize: 28, margin: "12px 0" }}>Weekly alerts</h1>
      {status === "loading" && <p className="note">Unsubscribing…</p>}
      {status === "done" && <p className="note ok">{message}</p>}
      {status === "error" && (
        <p className="note" style={{ color: "var(--urgent)" }}>
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
          <p className="note">Loading…</p>
        </main>
      }
    >
      <UnsubscribeInner />
    </Suspense>
  );
}
