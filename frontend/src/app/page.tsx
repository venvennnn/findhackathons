"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AlertsSection } from "@/components/AlertsSection";
import { SubmitCompetition } from "@/components/SubmitCompetition";
import { TeammateSignal } from "@/components/TeammateSignal";
import {
  DEFAULT_FEED_SOURCES,
  DOMAIN_OPTIONS,
  DomainCategory,
  Listing,
  MATCH_EXAMPLES,
  PLATFORM_OPTIONS,
  SkillLevel,
  SourceCount,
  SourcePlatform,
  getListings,
  getSources,
  inferProfile,
  matchHackathons,
  sourcesParam,
} from "@/lib/api";
import {
  daysUntil,
  domainLabel,
  effortEstimate,
  formatPrize,
  interestCount,
  isSoloFriendly,
  openInIndia,
} from "@/lib/utils";

type SortKey = "fit" | "soon" | "launch" | "prize" | "interest";

type EnrichedListing = Listing & {
  daysLeft: number | null;
  fit?: number;
  reason: string;
};

const THINKING = [
  "Reading what you wrote",
  "Checking eligibility",
  "Scoring open listings",
  "Ranking your shortlist",
];

export default function HomePage() {
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [levels, setLevels] = useState<Set<SkillLevel>>(new Set());
  const [domains, setDomains] = useState<Set<DomainCategory>>(new Set());
  const [platforms, setPlatforms] = useState<Set<SourcePlatform>>(new Set());
  const [flags, setFlags] = useState<
    Set<"solo" | "starter" | "india" | "prize" | "students" | "farHorizon">
  >(new Set());
  const [sort, setSort] = useState<SortKey>("prize");

  const [matchText, setMatchText] = useState("");
  const [matching, setMatching] = useState(false);
  const [matchOn, setMatchOn] = useState(false);
  const [matchNote, setMatchNote] = useState("Two or three sentences works best");
  const [thinkIdx, setThinkIdx] = useState(0);
  const [fitById, setFitById] = useState<
    Record<string, { fit: number; reason: string }>
  >({});
  const [matchSkill, setMatchSkill] = useState<SkillLevel>("beginner");
  const [matchDomains, setMatchDomains] = useState<DomainCategory[]>([]);
  const [sourceRows, setSourceRows] = useState<SourceCount[]>([]);

  const studentsOnly = flags.has("students");
  const farHorizon = flags.has("farHorizon");
  const prizeOnly = flags.has("prize");

  const feedSources = useMemo((): SourcePlatform[] => {
    if (platforms.size > 0) return Array.from(platforms);
    return [...DEFAULT_FEED_SOURCES];
  }, [platforms]);

  const feedKey = sourcesParam(feedSources);

  useEffect(() => {
    let cancelled = false;
    getSources()
      .then((data) => {
        if (!cancelled) setSourceRows(data.sources);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const data = await getListings({
          limit: "1000",
          has_prize: prizeOnly ? "true" : "false",
          sources: feedKey,
          max_deadline_days: farHorizon ? "0" : "90",
          ...(studentsOnly ? { students_only: "true" } : {}),
        });
        if (!cancelled) {
          setListings(data);
          getSources()
            .then((src) => {
              if (!cancelled) setSourceRows(src.sources);
            })
            .catch(() => undefined);
        }
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
  }, [prizeOnly, feedKey, farHorizon, studentsOnly]);

  const enriched: EnrichedListing[] = useMemo(() => {
    return listings.map((listing, index) => {
      const scored = fitById[listing.id];
      const baseFit = scored?.fit ?? Math.max(20, 70 - index * 3);
      return {
        ...listing,
        daysLeft: daysUntil(listing.deadline_utc),
        fit: matchOn ? baseFit : undefined,
        reason:
          scored?.reason ||
          listing.fit_reason ||
          listing.skill_floor_reasoning ||
          `${listing.organizer} · ${listing.skill_floor} floor`,
      };
    });
  }, [listings, fitById, matchOn]);

  const filtered = useMemo(() => {
    return enriched.filter((listing) => {
      if (listing.daysLeft !== null && listing.daysLeft < 0) return false;
      if (levels.size && !levels.has(listing.skill_floor)) return false;
      if (domains.size && !listing.domains.some((d) => domains.has(d))) return false;
      if (flags.has("solo") && !isSoloFriendly(listing)) return false;
      if (flags.has("starter") && !listing.has_starter_code) return false;
      if (flags.has("india") && !openInIndia(listing)) return false;
      return true;
    });
  }, [enriched, levels, domains, flags]);

  const sorted = useMemo(() => {
    return filtered.slice().sort((a, b) => {
      if (sort === "fit" && matchOn) {
        return (b.fit || 0) - (a.fit || 0) || (a.daysLeft ?? 999) - (b.daysLeft ?? 999);
      }
      if (sort === "interest") {
        return (
          interestCount(b) - interestCount(a) ||
          (b.prize_pool_usd || 0) - (a.prize_pool_usd || 0) ||
          (a.daysLeft ?? 999) - (b.daysLeft ?? 999)
        );
      }
      if (sort === "soon") {
        return (a.daysLeft ?? 999) - (b.daysLeft ?? 999);
      }
      if (sort === "launch") {
        const aLaunch = a.created_at ? Date.parse(a.created_at) : 0;
        const bLaunch = b.created_at ? Date.parse(b.created_at) : 0;
        return bLaunch - aLaunch || (a.daysLeft ?? 999) - (b.daysLeft ?? 999);
      }
      if (sort === "prize") {
        return (b.prize_pool_usd || 0) - (a.prize_pool_usd || 0);
      }
      return interestCount(b) - interestCount(a);
    });
  }, [filtered, sort, matchOn]);

  const stats = useMemo(() => {
    const open = enriched.filter((l) => l.daysLeft === null || l.daysLeft >= 0);
    return {
      open: open.length,
      soon: open.filter((l) => l.daysLeft !== null && l.daysLeft <= 7).length,
      beginner: open.filter((l) => l.skill_floor === "beginner").length,
      solo: open.filter((l) => isSoloFriendly(l)).length,
    };
  }, [enriched]);

  const sourceCountByPlatform = useMemo(() => {
    const map: Partial<Record<SourcePlatform, number>> = {};
    for (const row of sourceRows) map[row.source] = row.count;
    return map;
  }, [sourceRows]);

  const sourceLabel = useMemo(() => {
    const names = sourceRows
      .filter((row) => row.in_default_feed && row.count > 0)
      .map((row) => row.label);
    const core = names.length ? names.join(", ") : "Kaggle";
    return `${core}, and many others`;
  }, [sourceRows]);

  function toggleLevel(level: SkillLevel) {
    setLevels((current) => {
      const next = new Set(current);
      if (next.has(level)) next.delete(level);
      else next.add(level);
      return next;
    });
  }

  function toggleFlag(
    flag: "solo" | "starter" | "india" | "prize" | "students" | "farHorizon",
  ) {
    setFlags((current) => {
      const next = new Set(current);
      if (next.has(flag)) next.delete(flag);
      else next.add(flag);
      return next;
    });
  }

  function toggleDomain(domain: DomainCategory) {
    setDomains((current) => {
      const next = new Set(current);
      if (next.has(domain)) next.delete(domain);
      else next.add(domain);
      return next;
    });
  }

  function togglePlatform(platform: SourcePlatform) {
    setPlatforms((current) => {
      const next = new Set(current);
      if (next.has(platform)) next.delete(platform);
      else next.add(platform);
      return next;
    });
  }

  function clearFilters() {
    setLevels(new Set());
    setDomains(new Set());
    setPlatforms(new Set());
    setFlags(new Set());
  }

  function bumpInterest(listingId: string, count: number) {
    setListings((current) =>
      current.map((item) =>
        item.id === listingId
          ? { ...item, teammate_interest_count: count }
          : item,
      ),
    );
  }

  async function runMatch() {
    const text = matchText.trim();
    if (text.length < 15) return;
    setMatching(true);
    setThinkIdx(0);
    const timer = window.setInterval(
      () => setThinkIdx((idx) => (idx + 1) % THINKING.length),
      900,
    );
    try {
      const inferred = inferProfile(text);
      setMatchSkill(inferred.skill_level);
      setMatchDomains(inferred.domains);
      const result = await matchHackathons({
        free_text: text,
        skill_level: inferred.skill_level,
        domains: inferred.domains,
        country: "IN",
        prefer_starter_code: inferred.prefer_starter_code,
        students_only_ok: true,
        can_travel: false,
        min_deadline_days: 0,
        limit: 20,
      });
      const next: Record<string, { fit: number; reason: string }> = {};
      result.matches.forEach((listing, index) => {
        next[listing.id] = {
          fit: Math.max(35, 96 - index * 7),
          reason:
            listing.fit_reason ||
            listing.skill_floor_reasoning ||
            "Matches your profile filters.",
        };
      });
      listings.forEach((listing) => {
        if (next[listing.id]) return;
        let fit = 28;
        if (inferred.domains.some((d) => listing.domains.includes(d))) fit += 18;
        if (listing.skill_floor === inferred.skill_level) fit += 14;
        if (inferred.prefer_starter_code && listing.has_starter_code) fit += 10;
        if (!openInIndia(listing)) fit = Math.min(fit, 18);
        next[listing.id] = {
          fit,
          reason: listing.skill_floor_reasoning || "Outside the top ranked shortlist.",
        };
      });
      setFitById(next);
      setMatchOn(true);
      setSort("fit");
      setMatchNote("Ready");
      document.getElementById("listings")?.scrollIntoView({ behavior: "smooth" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Matching failed");
      setMatchNote("Try again");
    } finally {
      window.clearInterval(timer);
      setMatching(false);
    }
  }

  function resetMatch() {
    setMatchOn(false);
    setFitById({});
    setMatchText("");
    setMatchNote("Two or three sentences works best");
    setSort("interest");
  }

  const ready = matchText.trim().length >= 15;
  const strongFits = matchOn
    ? sorted.filter((item) => (item.fit || 0) >= 60).length
    : 0;

  return (
    <>
      <header>
        <div className="wrap nav">
          <Link className="brand" href="/">
            <span aria-hidden />
            FindHackathons
          </Link>
          <div className="links">
            <a href="#matcher">Match me</a>
            <a href="#alerts">Friday email</a>
            <a href="#submit">Add one</a>
            <button
              type="button"
              className="btn"
              onClick={() => document.getElementById("alert-email")?.focus()}
            >
              Get alerts
            </button>
          </div>
        </div>
      </header>

      <section className="hero">
        <div className="wrap">
          <span className="tagline">
            <i aria-hidden />
            {loading
              ? "Loading open competitions…"
              : `${stats.open} open · ${sourceLabel}`}
          </span>
          <h1>Hackathons you can actually finish.</h1>
          <p className="lede">
            Every listing carries a skill floor, an eligibility note, and an
            honest estimate of how many weekends it costs. Ranked by whether
            you&apos;d survive it — and how many people are already looking for
            teammates.
          </p>
          <div className="stats">
            <div className="stat">
              <span className="n">{loading ? "—" : stats.open}</span>
              <span className="l">open now</span>
            </div>
            <div className="stat">
              <span className="n">{loading ? "—" : stats.soon}</span>
              <span className="l">closing in 7 days</span>
            </div>
            <div className="stat">
              <span className="n">{loading ? "—" : stats.beginner}</span>
              <span className="l">beginner friendly</span>
            </div>
            <div className="stat">
              <span className="n">{loading ? "—" : stats.solo}</span>
              <span className="l">solo friendly</span>
            </div>
          </div>
        </div>
      </section>

      <section className="matcher" id="matcher">
        <div className="wrap">
          <div className="mbox">
            <label className="sr" htmlFor="selfdesc">
              Describe your background and what you want
            </label>
            <textarea
              id="selfdesc"
              rows={3}
              value={matchText}
              onChange={(e) => {
                const value = e.target.value;
                setMatchText(value);
                const n = value.trim().length;
                setMatchNote(
                  n === 0
                    ? "Two or three sentences works best"
                    : n < 15
                      ? "A little more to go on…"
                      : "Ready",
                );
              }}
              onKeyDown={(e) => {
                if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
                  e.preventDefault();
                  void runMatch();
                }
              }}
              placeholder="Second-year CS student. Comfortable with Python and pandas, never deployed anything. Want something tabular I can do alone over two weekends."
            />
            <div className="mfoot">
              <span className="hint">
                {matching ? THINKING[thinkIdx] + "…" : matchNote}
              </span>
              {matchOn && (
                <button type="button" className="btn quiet" onClick={resetMatch}>
                  Start over
                </button>
              )}
              <button
                type="button"
                className="btn"
                disabled={!ready || matching}
                onClick={() => void runMatch()}
              >
                {matching
                  ? "Scoring…"
                  : matchOn
                    ? "Re-score"
                    : `Rank all ${listings.length || ""} for me`.trim()}
              </button>
            </div>
          </div>
          <div className="starters">
            {MATCH_EXAMPLES.map((example) => (
              <button
                key={example.label}
                type="button"
                className="chip"
                onClick={() => {
                  setMatchText(example.text);
                  setMatchNote("Ready");
                }}
              >
                {example.label}
              </button>
            ))}
          </div>
          {matchOn && (
            <div className="readout">
              <p>
                Read {stats.open} open listings. You&apos;re a strong fit for{" "}
                {strongFits}. Remove anything below to re-rank.
              </p>
              <div className="pills">
                <span className="pill">
                  {matchSkill}
                  <button type="button" aria-label="Clear match" onClick={resetMatch}>
                    ×
                  </button>
                </span>
                {matchDomains.map((domain) => (
                  <span className="pill" key={domain}>
                    {domainLabel(domain)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      <div className="toolbar" id="listings">
        <div className="wrap toolbar-stack">
          <div className="tool-row">
            <span className="tool-label">Level</span>
            <div className="tools">
              {(["beginner", "intermediate", "advanced"] as const).map((level) => (
                <button
                  key={level}
                  type="button"
                  className="filter"
                  aria-pressed={levels.has(level)}
                  onClick={() => toggleLevel(level)}
                >
                  {level[0].toUpperCase() + level.slice(1)}
                </button>
              ))}
              <span className="divider" aria-hidden />
              <button
                type="button"
                className="filter"
                aria-pressed={flags.has("solo")}
                onClick={() => toggleFlag("solo")}
              >
                Solo allowed
              </button>
              <button
                type="button"
                className="filter"
                aria-pressed={flags.has("starter")}
                onClick={() => toggleFlag("starter")}
              >
                Starter code
              </button>
              <button
                type="button"
                className="filter"
                aria-pressed={flags.has("india")}
                onClick={() => toggleFlag("india")}
              >
                Open in India
              </button>
              <button
                type="button"
                className="filter"
                aria-pressed={flags.has("prize")}
                onClick={() => toggleFlag("prize")}
              >
                Has prize
              </button>
              <button
                type="button"
                className="filter"
                aria-pressed={flags.has("students")}
                onClick={() => toggleFlag("students")}
              >
                Students only
              </button>
              <button
                type="button"
                className="filter"
                aria-pressed={flags.has("farHorizon")}
                onClick={() => toggleFlag("farHorizon")}
              >
                Farther than 90 days
              </button>
            </div>
          </div>

          <div className="tool-row">
            <span className="tool-label">Track</span>
            <div className="tools">
              {DOMAIN_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  className="filter"
                  aria-pressed={domains.has(option.value)}
                  onClick={() => toggleDomain(option.value)}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          <div className="tool-row">
            <span className="tool-label">Platform</span>
            <div className="tools">
              {PLATFORM_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  className="filter"
                  aria-pressed={platforms.has(option.value)}
                  onClick={() => togglePlatform(option.value)}
                >
                  {option.label}
                  {sourceCountByPlatform[option.value]
                    ? ` · ${sourceCountByPlatform[option.value]}`
                    : ""}
                </button>
              ))}
            </div>
          </div>

          <div className="tool-row">
            <span className="tool-label">Sort</span>
            <div className="tools">
              <button
                type="button"
                className="filter"
                aria-pressed={sort === "soon"}
                onClick={() => setSort("soon")}
              >
                Time remaining
              </button>
              <button
                type="button"
                className="filter"
                aria-pressed={sort === "launch"}
                onClick={() => setSort("launch")}
              >
                Launch date
              </button>
              <button
                type="button"
                className="filter"
                aria-pressed={sort === "prize"}
                onClick={() => setSort("prize")}
              >
                Prize money
              </button>
              <button
                type="button"
                className="filter"
                aria-pressed={sort === "interest"}
                onClick={() => setSort("interest")}
              >
                Interested
              </button>
              {matchOn && (
                <button
                  type="button"
                  className="filter"
                  aria-pressed={sort === "fit"}
                  onClick={() => setSort("fit")}
                >
                  Best match
                </button>
              )}
              <div className="right">
                <span className="count">
                  {loading ? "…" : `${sorted.length} of ${stats.open}`}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <main className="wrap">
        <div className="grid">
          {error && <div className="error-banner">{error}</div>}
          {!loading && !sorted.length && (
            <div className="empty">
              <h3>Nothing matches those filters.</h3>
              <p>Clear a few chips and try again — or include no-prize comps.</p>
              <button type="button" className="btn quiet" onClick={clearFilters}>
                Clear filters
              </button>
            </div>
          )}
          {sorted.map((listing) => {
            const urgent = listing.daysLeft !== null && listing.daysLeft <= 7;
            const interested = interestCount(listing);
            const prize = listing.prize_pool_usd || 0;
            return (
              <article
                key={listing.id}
                className={`card${urgent ? " urgent" : ""}`}
              >
                <div className="card-top">
                  {interested > 0 && (
                    <span className="interest" title="People looking for teammates">
                      <strong>{interested}</strong> looking
                    </span>
                  )}
                  <span className="src">{listing.source}</span>
                  {typeof listing.fit === "number" && (
                    <span className="fit">{listing.fit}% fit</span>
                  )}
                  <span className="days">
                    {listing.daysLeft === null
                      ? "Deadline TBA"
                      : listing.daysLeft === 0
                        ? "Closes today"
                        : `${listing.daysLeft} days left`}
                  </span>
                </div>
                <h3>
                  <a href={listing.url} target="_blank" rel="noreferrer">
                    {listing.title}
                  </a>
                </h3>
                <p className="why">
                  {listing.reason.charAt(0).toUpperCase() + listing.reason.slice(1)}
                  {listing.reason.endsWith(".") ? "" : "."}
                </p>
                <div className="tags">
                  {listing.domains.slice(0, 3).map((domain) => (
                    <span className="tag" key={domain}>
                      {domainLabel(domain)}
                    </span>
                  ))}
                  <span className="tag">{listing.skill_floor}</span>
                  {isSoloFriendly(listing) ? (
                    <span className="tag">solo ok</span>
                  ) : (
                    <span className="tag">team</span>
                  )}
                  {listing.has_starter_code && (
                    <span className="tag">starter code</span>
                  )}
                  {listing.students_only && <span className="tag">students</span>}
                  {listing.community_submitted && (
                    <span className="tag">added by someone</span>
                  )}
                </div>
                <div className="card-foot">
                  <span className={`prize${prize ? "" : " none"}`}>
                    {formatPrize(listing.prize_pool_usd, listing.prize_text)}
                  </span>
                  <span className="effort">{effortEstimate(listing)}</span>
                </div>
                <div className="card-extra">
                  <TeammateSignal
                    listing={listing}
                    onInterest={(count) => bumpInterest(listing.id, count)}
                  />
                </div>
              </article>
            );
          })}
        </div>
      </main>

      <AlertsSection skillLevel={matchSkill} domains={matchDomains} />
      <SubmitCompetition />

      <footer>
        <div className="wrap fw">
          <span>FindHackathons</span>
          <span>Kaggle competitions by default. People can add others.</span>
          <span className="push">
            {loading ? "" : `${stats.open} open competitions`}
          </span>
        </div>
      </footer>
    </>
  );
}
