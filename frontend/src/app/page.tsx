"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AlertCapture } from "@/components/AlertCapture";
import { ListingResult } from "@/components/ListingResult";
import { SiteHeader } from "@/components/SiteHeader";
import {
  DOMAIN_OPTIONS,
  DomainCategory,
  Listing,
  SkillLevel,
  getListings,
} from "@/lib/api";

export default function HomePage() {
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [skill, setSkill] = useState<SkillLevel | "all">("all");
  const [domain, setDomain] = useState<DomainCategory | "all">("all");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const params: Record<string, string> = { limit: "40" };
        if (skill !== "all") params.skill_level = skill;
        const data = await getListings(params);
        if (!cancelled) setListings(data);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load listings");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [skill]);

  const filtered = useMemo(() => {
    if (domain === "all") return listings;
    return listings.filter((item) => item.domains.includes(domain));
  }, [listings, domain]);

  return (
    <main className="min-h-screen bg-white">
      <SiteHeader />

      <div className="mx-auto max-w-5xl px-5 pb-16 pt-4">
        <div className="max-w-xl">
          <h1 className="text-3xl font-semibold tracking-tight text-ink md:text-4xl">
            Hackathons you can finish
          </h1>
          <p className="mt-3 text-base leading-relaxed text-muted">
            Active listings with skill level, eligibility, and starter-code signals —
            filtered for students and early-career builders.
          </p>
        </div>

        <div className="mt-10 grid gap-12 lg:grid-cols-[minmax(0,1fr)_280px]">
          <section>
            <div className="flex flex-wrap items-center gap-2 border-b border-line pb-4">
              {(["all", "beginner", "intermediate", "advanced"] as const).map(
                (value) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setSkill(value)}
                    className={`px-2.5 py-1 text-sm ${
                      skill === value
                        ? "bg-ink text-white"
                        : "text-muted hover:text-ink"
                    }`}
                  >
                    {value === "all" ? "All" : value}
                  </button>
                ),
              )}
              <span className="mx-1 hidden h-4 w-px bg-line sm:inline-block" />
              <select
                value={domain}
                onChange={(e) =>
                  setDomain((e.target.value || "all") as DomainCategory | "all")
                }
                className="border-0 bg-transparent py-1 text-sm text-muted outline-none"
              >
                <option value="all">All domains</option>
                {DOMAIN_OPTIONS.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
              <span className="ml-auto text-xs text-faint">
                {loading ? "…" : `${filtered.length} open`}
              </span>
            </div>

            {loading && <p className="py-12 text-sm text-muted">Loading…</p>}
            {error && (
              <div className="space-y-2 py-12">
                <p className="text-sm text-[var(--danger)]">{error}</p>
                <p className="text-sm text-muted">
                  Set Vercel env <code className="text-ink">BACKEND_URL</code> to
                  your Railway URL, then redeploy. Check{" "}
                  <code className="text-ink">/api/health</code> on Railway first.
                </p>
              </div>
            )}
            {!loading && !error && filtered.length === 0 && (
              <p className="py-12 text-sm text-muted">
                Nothing matches right now. Try Match me on the right, or join alerts.
              </p>
            )}
            <div className="divide-y divide-line">
              {!loading &&
                !error &&
                filtered.map((listing) => (
                  <ListingResult key={listing.id} listing={listing} />
                ))}
            </div>
          </section>

          <aside className="lg:pt-1">
            <div className="lg:sticky lg:top-8">
              <h2 className="text-sm font-medium text-ink">Match me</h2>
              <p className="mt-2 text-sm leading-relaxed text-muted">
                Answer a few questions and get a shortlist ranked for what you can
                actually ship this month.
              </p>
              <Link
                href="/onboarding"
                className="mt-5 inline-flex bg-ink px-4 py-2.5 text-sm font-medium text-white transition hover:bg-neutral-800"
              >
                Start matching
              </Link>
              <ul className="mt-6 space-y-2 text-sm text-muted">
                <li>Skill floor & starter code</li>
                <li>Country / student eligibility</li>
                <li>One-sentence fit reason</li>
              </ul>
              <div className="mt-8">
                <AlertCapture />
              </div>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}