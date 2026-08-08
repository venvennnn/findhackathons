"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

/** Shortlist is now scored on the homepage. */
export default function FeedPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/");
  }, [router]);

  return (
    <main className="wrap" style={{ padding: "80px 0" }}>
      <p className="eyebrow">Shortlist</p>
      <h1 style={{ fontFamily: "var(--display)", fontSize: "2rem", margin: 0 }}>
        Taking you home…
      </h1>
      <p style={{ color: "var(--ink-2)", marginTop: 12 }}>
        Use <Link href="/#matcher">Match me</Link> on the homepage.
      </p>
    </main>
  );
}