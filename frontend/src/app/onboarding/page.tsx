"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

/** Match me now lives on the homepage. Keep this route as a friendly redirect. */
export default function OnboardingPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/#matcher");
  }, [router]);

  return (
    <main className="wrap" style={{ padding: "80px 0" }}>
      <p className="eyebrow">Match me</p>
      <h1 style={{ fontFamily: "var(--display)", fontSize: "2rem", margin: 0 }}>
        Taking you to the matcher…
      </h1>
      <p style={{ color: "var(--ink-2)", marginTop: 12 }}>
        Or <Link href="/#matcher">click here</Link>.
      </p>
    </main>
  );
}