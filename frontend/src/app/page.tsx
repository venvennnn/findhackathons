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

const SKILL_FILTERS: { value: SkillLevel | "all"; label: string }[] = [
  { value: "all", label: "All levels" },
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
];

const SOURCE_FILTERS = [
  { value: "all", label: "All platforms" },
  { value: "devfolio", label: "Devfolio" },
  { value: "unstop", label: "Unstop" },
  { value: "kaggle", label: "Kaggle" },
  { value: "devpost", label: "Devpost" },
];

export default function HomePage() {
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [skill, setSkill] = useState<SkillLevel | "all">("all");
  const [domain, setDomain] = useState<DomainCategory | "all">("all");
  const [source, setSource] = useState("all");
  const [starterOnly, setStarterOnly] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const params: Record<string, string> = { limit: "40" };
        if (skill !== "all") params.skill_level = skill;
        if (source !== "all") params.source = source;
        if (starterOnly) params.has_starter_code = "true";
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
  }, [skill, source, starterOnly]);

  const filtered = useMemo(() => {
    if (domain === "all") return listings;
    return listings.filter((item) => item.domains.includes(domain));
  }, [listings, domain]);

  function resetFilters() {
    setSkill("all");
    setDomain("all");
    setSource("all");
    setStarterOnly(false);
  }

  return (
    <main className="min-h-screen bg-white">
      <SiteHeader />
      <AlertCapture variant="banner" />

      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-8 md:grid-cols-[220px_1fr] md:px-6 lg:grid-cols-[240px_1fr]">
        <aside className="space-y-7 text-sm">
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-faint">
              Skill level
            </p>
            <div className="flex flex-wrap gap-1.5">
              {SKILL_FILTERS.map((item) => (
                <button
                  key={item.value}
                  type="button"
                  onClick={() => setSkill(item.value)}
                  className={`rounded border px-2.5 py-1 text-xs ${
                    skill === item.value
                      ? "border-ink bg-ink text-white"
                      : "border-line text-muted hover:border-ink/30"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-faint">
              Domains
            </p>
            <div className="flex flex-wrap gap-1.5">
              <button
                type="button"
                onClick={() => setDomain("all")}
                className={`rounded border px-2.5 py-1 text-xs ${
                  domain === "all"
                    ? "border-ink bg-ink text-white"
                    : "border-line text-muted hover:border-ink/30"
                }`}
              >
                All
              </button>
              {DOMAIN_OPTIONS.map((item) => (
                <button
                  key={item.value}
                  type="button"
                  onClick={() => setDomain(item.value)}
                  className={`rounded border px-2.5 py-1 text-xs ${
                    domain === item.value
                      ? "border-ink bg-ink text-white"
                      : "border-line text-muted hover:border-ink/30"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-faint">
              Platform
            </p>
            <div className="flex flex-wrap gap-1.5">
              {SOURCE_FILTERS.map((item) => (
                <button
                  key={item.value}
                  type="button"
                  onClick={() => setSource(item.value)}
                  className={`rounded border px-2.5 py-1 text-xs ${
                    source === item.value
                      ? "border-ink bg-ink text-white"
                      : "border-line text-muted hover:border-ink/30"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          <label className="flex items-center gap-2 text-xs text-muted">
            <input
              type="checkbox"
              checked={starterOnly}
              onChange={(e) => setStarterOnly(e.target.checked)}
              className="size-3.5 accent-accent"
            />
            Has starter code
          </label>

          <Link
            href="/onboarding"
            className="inline-block text-sm font-medium text-link hover:underline"
          >
            Personalized matching →
          </Link>
        </aside>

        <section>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-faint">
              Competitions ({loading ? "…" : filtered.length})
            </h2>
            <button
              type="button"
              onClick={resetFilters}
              className="text-xs text-muted hover:text-ink"
            >
              Reset filters
            </button>
          </div>

          {loading && <p className="py-10 text-sm text-muted">Loading competitions…</p>}
          {error && (
            <p className="py-10 text-sm text-[var(--danger)]">
              {error}. Is the API running?
            </p>
          )}
          {!loading && !error && filtered.length === 0 && (
            <div className="space-y-4 py-10">
              <p className="text-sm text-muted">
                No competitions match these filters. Try broadening them or get alerts.
              </p>
              <AlertCapture variant="panel" />
            </div>
          )}
          {!loading &&
            !error &&
            filtered.map((listing) => (
              <ListingResult key={listing.id} listing={listing} />
            ))}
        </section>
      </div>
    </main>
  );
}