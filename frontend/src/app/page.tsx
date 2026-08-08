"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AlertsSection } from "@/components/AlertsSection";
import { DeadlineHorizon } from "@/components/DeadlineHorizon";
import { SubmitCompetition } from "@/components/SubmitCompetition";
import { TeammateSignal } from "@/components/TeammateSignal";
import {
  DOMAIN_OPTIONS,
  DomainCategory,
  Listing,
  MATCH_EXAMPLES,
  SkillLevel,
  getListings,
  inferProfile,
  matchHackathons,
} from "@/lib/api";
import {
  daysUntil,
  domainLabel,
  finishScore,
  formatPrize,
  openInIndia,
  runwaySpent,
  urgency,
} from "@/lib/utils";

type SortKey = "fit" | "finish" | "soon" | "prize";

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
  const [query, setQuery] = useState("");
  const [level, setLevel] = useState<SkillLevel | "all">("all");
  const [domains, setDomains] = useState<Set<DomainCategory>>(new Set());
  const [flags, setFlags] = useState<Set<"starter" | "india" | "noPrize">>(
    new Set(),
  );
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

  const includeNoPrize = flags.has("noPrize");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError("");
      try {
        // Default: cash-prize comps only. Toggle "Include no-prize" to widen.
        const data = await getListings({
          limit: "60",
          has_prize: includeNoPrize ? "false" : "true",
        });
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
  }, [includeNoPrize]);

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
          "Open listing with structured eligibility metadata.",
      };
    });
  }, [listings, fitById, matchOn]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return enriched.filter((listing) => {
      if (listing.daysLeft !== null && listing.daysLeft < 0) return false;
      if (level !== "all" && listing.skill_floor !== level) return false;
      if (domains.size && !listing.domains.some((d) => domains.has(d))) return false;
      if (flags.has("starter") && !listing.has_starter_code) return false;
      if (flags.has("india") && !openInIndia(listing)) return false;
      if (
        q &&
        !(
          listing.title +
          " " +
          listing.organizer +
          " " +
          listing.domains.map(domainLabel).join(" ")
        )
          .toLowerCase()
          .includes(q)
      ) {
        return false;
      }
      return true;
    });
  }, [enriched, query, level, domains, flags]);

  const sorted = useMemo(() => {
    return filtered.slice().sort((a, b) => {
      if (sort === "fit" && matchOn) {
        return (b.fit || 0) - (a.fit || 0) || (a.daysLeft ?? 999) - (b.daysLeft ?? 999);
      }
      if (sort === "soon") return (a.daysLeft ?? 999) - (b.daysLeft ?? 999);
      if (sort === "prize")
        return (b.prize_pool_usd || 0) - (a.prize_pool_usd || 0);
      return finishScore(b) - finishScore(a);
    });
  }, [filtered, sort, matchOn]);

  const activeFilters =
    query ||
    level !== "all" ||
    domains.size > 0 ||
    flags.has("starter") ||
    flags.has("india") ||
    flags.has("noPrize");

  function toggleDomain(domain: DomainCategory) {
    setDomains((current) => {
      const next = new Set(current);
      if (next.has(domain)) next.delete(domain);
      else next.add(domain);
      return next;
    });
  }

  function toggleFlag(flag: "starter" | "india" | "noPrize") {
    setFlags((current) => {
      const next = new Set(current);
      if (next.has(flag)) next.delete(flag);
      else next.add(flag);
      return next;
    });
  }

  function clearFilters() {
    setQuery("");
    setLevel("all");
    setDomains(new Set());
    setFlags(new Set());
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
      // Soft-score remaining listings so the full list stays useful
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
      document.querySelector(".filters")?.scrollIntoView({ behavior: "smooth" });
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
    setSort("finish");
  }

  const ready = matchText.trim().length >= 15;

  return (
    <>
      <header className="topbar">
        <div className="wrap">
          <Link className="mark" href="/">
            find<span>hackathons</span>
          </Link>
          <nav className="topnav">
            <a className="tlink" href="#alerts">
              Weekly alerts
            </a>
            <a className="tlink solid" href="#matcher">
              Match me
            </a>
          </nav>
        </div>
      </header>

      <section className="hero wrap">
        <p className="eyebrow">
          Live inventory · {loading ? "…" : `${listings.length} open`}
        </p>
        <h1>
          Hackathons you can <em>actually finish.</em>
        </h1>
        <p className="lede">
          Every listing shows how much runway is left, how much work it takes, and
          whether you&apos;re eligible — before you click through.
        </p>

        <DeadlineHorizon listings={sorted.length ? sorted : listings} />

        <section className="matcher" id="matcher" aria-labelledby="mtitle">
          <p className="eyebrow">Match me</p>
          <h2 id="mtitle">Describe yourself. In your own words.</h2>
          <p className="sub">
            No dropdowns, no signup. Say where you&apos;re at and what you want out
            of this, and every listing below gets read and scored against it.
          </p>

          <div className="prompt">
            <textarea
              id="mq"
              rows={3}
              aria-label="Describe yourself"
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
              placeholder="I'm a credit risk data scientist — strong on tabular modelling, never touched deep learning. Free most evenings for the next month and I want something that stretches me without needing a GPU."
            />
            <div className="mfoot">
              <button
                className="mgo"
                type="button"
                disabled={!ready || matching}
                onClick={() => void runMatch()}
              >
                {matching
                  ? "Scoring…"
                  : matchOn
                    ? "Re-score"
                    : `Score all ${listings.length || ""} listings`.trim()}
              </button>
              <span className="mnote">
                {matching ? (
                  <span className="thinking">
                    <i />
                    {THINKING[thinkIdx]}…
                  </span>
                ) : (
                  matchNote
                )}
              </span>
              {matchOn && (
                <button className="mreset" type="button" onClick={resetMatch}>
                  Start over
                </button>
              )}
            </div>
          </div>

          <div className="examples">
            <span className="exlabel">Or start from</span>
            {MATCH_EXAMPLES.map((example) => (
              <button
                key={example.label}
                type="button"
                className="ex"
                onClick={() => {
                  setMatchText(example.text);
                  setMatchNote("Ready");
                }}
              >
                {example.label}
              </button>
            ))}
          </div>
        </section>
      </section>

      <div className="filters">
        <div className="wrap">
          <div className="frow">
            <div className="search">
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.4"
              >
                <circle cx="11" cy="11" r="7" />
                <path d="M20 20l-4-4" />
              </svg>
              <input
                type="search"
                placeholder="Search by name, host, or tech…"
                aria-label="Search hackathons"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
            <div className="seg" role="group" aria-label="Skill level">
              {(["all", "beginner", "intermediate", "advanced"] as const).map(
                (value) => (
                  <button
                    key={value}
                    type="button"
                    data-level={value}
                    aria-pressed={level === value}
                    onClick={() => setLevel(value)}
                  >
                    {value === "all" ? "All levels" : value[0].toUpperCase() + value.slice(1)}
                  </button>
                ),
              )}
            </div>
            <div className="sortwrap">
              <label htmlFor="sort">Sort</label>
              <select
                id="sort"
                value={sort}
                onChange={(e) => setSort(e.target.value as SortKey)}
              >
                {matchOn && <option value="fit">Best match for you</option>}
                <option value="finish">Best chance of finishing</option>
                <option value="soon">Closing soonest</option>
                <option value="prize">Biggest prize</option>
              </select>
            </div>
          </div>
          <div className="frow">
            <div className="chips" role="group" aria-label="Domain">
              {DOMAIN_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  className="chip"
                  aria-pressed={domains.has(option.value)}
                  onClick={() => toggleDomain(option.value)}
                >
                  {option.label}
                </button>
              ))}
              <button
                type="button"
                className="chip flag"
                aria-pressed={flags.has("noPrize")}
                onClick={() => toggleFlag("noPrize")}
              >
                Include no-prize
              </button>
              <button
                type="button"
                className="chip flag"
                aria-pressed={flags.has("starter")}
                onClick={() => toggleFlag("starter")}
              >
                Has starter code
              </button>
              <button
                type="button"
                className="chip flag"
                aria-pressed={flags.has("india")}
                onClick={() => toggleFlag("india")}
              >
                Open in India
              </button>
            </div>
          </div>
        </div>
      </div>

      <main className="wrap">
        <div className="meta">
          <span>
            {loading ? (
              "Loading…"
            ) : matchOn ? (
              <>
                <b>{sorted.filter((item) => (item.fit || 0) >= 60).length}</b> strong
                matches · <b>{sorted.length}</b> open in total
              </>
            ) : (
              <>
                <b>{sorted.length}</b>{" "}
                {includeNoPrize ? "open" : "with prizes"} ·{" "}
                <b>{sorted.filter((item) => (item.daysLeft ?? 99) <= 7).length}</b>{" "}
                close this week
              </>
            )}
          </span>
          {activeFilters && (
            <button className="clearbtn" type="button" onClick={clearFilters}>
              Clear filters
            </button>
          )}
        </div>

        {error && <div className="error-banner">{error}</div>}

        <ul className="list">
          {loading &&
            Array.from({ length: 4 }).map((_, idx) => (
              <li key={idx} className="skel" />
            ))}

          {!loading && !sorted.length && (
            <li>
              <div className="empty">
                <h3>Nothing open with those filters.</h3>
                <p>
                  The narrowest filter here is usually skill level. Widening it
                  normally brings back four or five listings.
                </p>
                <button type="button" onClick={() => setLevel("all")}>
                  Show all levels
                </button>
              </div>
            </li>
          )}

          {!loading &&
            sorted.map((listing, index) => {
              const u = urgency(listing.daysLeft);
              const spent = runwaySpent(listing.daysLeft);
              const best = matchOn && sort === "fit" && index === 0;
              const indiaOk = openInIndia(listing);
              return (
                <li
                  key={listing.id}
                  id={`card-${listing.id}`}
                  className={`card ${u}${best ? " best" : ""}`}
                >
                  {best && <span className="best-flag">Best match</span>}
                  <div className="runway" aria-hidden="true">
                    <div className="spent" style={{ width: `${spent}%` }} />
                    <div className="left" style={{ width: `${100 - spent}%` }} />
                  </div>
                  <div className="body">
                    <div className="head">
                      <div>
                        {matchOn && listing.fit != null && (
                          <span className="fit">
                            <b>{listing.fit}%</b>
                            <u>fit for you</u>
                          </span>
                        )}
                        <h3 className="title">
                          <a href={listing.url} target="_blank" rel="noreferrer">
                            {listing.title}
                          </a>
                        </h3>
                        <p className="host">
                          {listing.organizer} · {listing.source}
                        </p>
                      </div>
                      <div className="count">
                        <b>
                          {listing.daysLeft == null ? "—" : `${listing.daysLeft}d`}
                        </b>
                        <u>
                          {(listing.daysLeft ?? 99) <= 7 ? "closing" : "of runway"}
                        </u>
                      </div>
                    </div>
                    <p className={`why${matchOn ? " mine" : ""}`}>{listing.reason}</p>
                    <div className="tags">
                      <span className="tag lv">{listing.skill_floor}</span>
                      {listing.domains.slice(0, 2).map((domain) => (
                        <span className="tag" key={domain}>
                          {domainLabel(domain)}
                        </span>
                      ))}
                      {listing.has_starter_code && (
                        <span className="tag ok">starter code</span>
                      )}
                      {listing.students_only && (
                        <span className="tag ok">students</span>
                      )}
                      {!indiaOk && <span className="tag warn">region-locked</span>}
                    </div>
                    <div className="foot">
                      <span className="money">{formatPrize(listing.prize_pool_usd)}</span>
                      <span>
                        {listing.requires_travel ? "Travel required" : "Online / remote ok"}
                      </span>
                      {listing.team_size_max != null && (
                        <span>Team ≤ {listing.team_size_max}</span>
                      )}
                    </div>
                    <TeammateSignal listing={listing} />
                  </div>
                </li>
              );
            })}
        </ul>
      </main>

      <AlertsSection
        skillLevel={matchOn ? matchSkill : "beginner"}
        domains={matchOn ? matchDomains : []}
      />

      <SubmitCompetition />

      <div className="wrap colophon">
        FindHackathons · structured metadata from Devfolio, Unstop, Kaggle, and Devpost.
      </div>
    </>
  );
}