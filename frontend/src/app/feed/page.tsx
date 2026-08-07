"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { AlertCapture } from "@/components/AlertCapture";
import { ListingResult } from "@/components/ListingResult";
import { SiteHeader } from "@/components/SiteHeader";
import {
  DomainCategory,
  MatchResponse,
  SkillLevel,
  matchHackathons,
} from "@/lib/api";

function FeedContent() {
  const params = useSearchParams();
  const [data, setData] = useState<MatchResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const profileId = params.get("profile_id") || undefined;
  const skillLevel = (params.get("skill_level") as SkillLevel) || "beginner";
  const domains = (params.get("domains") || "web-dev")
    .split(",")
    .filter(Boolean) as DomainCategory[];
  const country = params.get("country") || "IN";
  const freeText = params.get("free_text") || undefined;
  const preferStarter = params.get("prefer_starter_code") !== "false";
  const studentsOnlyOk = params.get("students_only_ok") !== "false";
  const canTravel = params.get("can_travel") === "true";

  useEffect(() => {
    let cancelled = false;
    async function run() {
      setLoading(true);
      setError("");
      try {
        const result = await matchHackathons({
          profile_id: profileId,
          skill_level: skillLevel,
          domains,
          country,
          free_text: freeText,
          prefer_starter_code: preferStarter,
          students_only_ok: studentsOnlyOk,
          can_travel: canTravel,
          min_deadline_days: 7,
          limit: 5,
        });
        if (!cancelled) setData(result);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load matches");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    run();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.toString()]);

  return (
    <main className="min-h-screen bg-white">
      <SiteHeader />
      <div className="mx-auto max-w-3xl px-4 py-10 md:px-6">
        <div className="flex flex-wrap items-end justify-between gap-3 border-b border-line pb-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-ink">
              Your shortlist
            </h1>
            <p className="mt-1 text-sm text-muted">
              Ranked for finishability and fit
            </p>
          </div>
          <Link href="/onboarding" className="text-sm text-link hover:underline">
            Refine filters
          </Link>
        </div>

        {loading && <p className="mt-8 text-sm text-muted">Ranking competitions…</p>}
        {error && <p className="mt-8 text-sm text-[var(--danger)]">{error}</p>}

        {!loading && !error && data && (
          <>
            {data.message && (
              <p className="mt-4 text-sm text-muted">{data.message}</p>
            )}
            <p className="mt-2 text-xs uppercase tracking-wide text-faint">
              {data.total_candidates} candidate
              {data.total_candidates === 1 ? "" : "s"}
              {data.broadened ? " · broadened" : ""}
            </p>

            <div className="mt-6">
              {data.matches.length === 0 ? (
                <p className="text-sm text-muted">
                  No active competitions survived your filters. Subscribe below for
                  alerts.
                </p>
              ) : (
                data.matches.map((listing) => (
                  <ListingResult key={listing.id} listing={listing} />
                ))
              )}
            </div>

            <div className="mt-8">
              <AlertCapture
                skillLevel={skillLevel}
                domains={domains}
                country={country}
                freeText={freeText}
                profileId={profileId}
              />
            </div>
          </>
        )}
      </div>
    </main>
  );
}

export default function FeedPage() {
  return (
    <Suspense
      fallback={
        <main className="grid min-h-screen place-items-center bg-white text-muted">
          Loading…
        </main>
      }
    >
      <FeedContent />
    </Suspense>
  );
}