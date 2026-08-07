"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useMemo, useState, useTransition } from "react";
import { SiteHeader } from "@/components/SiteHeader";
import {
  DOMAIN_OPTIONS,
  DomainCategory,
  SkillLevel,
  createProfile,
} from "@/lib/api";

function OnboardingForm() {
  const router = useRouter();
  const params = useSearchParams();
  const alertsMode = params.get("mode") === "alerts";
  const [pending, startTransition] = useTransition();
  const [error, setError] = useState("");

  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [freeText, setFreeText] = useState(
    "I know basic Python and React. Looking for beginner-friendly campus hackathons with starter code.",
  );
  const [skillLevel, setSkillLevel] = useState<SkillLevel>("beginner");
  const [domains, setDomains] = useState<DomainCategory[]>(["web-dev", "tabular"]);
  const [country, setCountry] = useState("IN");
  const [studentsOnlyOk, setStudentsOnlyOk] = useState(true);
  const [canTravel, setCanTravel] = useState(false);
  const [preferStarter, setPreferStarter] = useState(true);
  const [alertsEnabled, setAlertsEnabled] = useState(alertsMode);

  const domainSet = useMemo(() => new Set(domains), [domains]);

  function toggleDomain(domain: DomainCategory) {
    setDomains((current) =>
      current.includes(domain)
        ? current.filter((item) => item !== domain)
        : [...current, domain],
    );
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    startTransition(async () => {
      try {
        const profile = await createProfile({
          display_name: displayName || undefined,
          email: email || undefined,
          free_text: freeText,
          skill_level: skillLevel,
          domains,
          country,
          students_only_ok: studentsOnlyOk,
          can_travel: canTravel,
          prefer_starter_code: preferStarter,
          min_deadline_days: 7,
          alerts_enabled: alertsEnabled && Boolean(email),
        });

        const query = new URLSearchParams({
          profile_id: profile.id,
          skill_level: skillLevel,
          domains: domains.join(","),
          country,
          free_text: freeText,
          prefer_starter_code: String(preferStarter),
          students_only_ok: String(studentsOnlyOk),
          can_travel: String(canTravel),
        });
        router.push(`/feed?${query.toString()}`);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not save profile");
      }
    });
  }

  return (
    <main className="min-h-screen bg-white">
      <SiteHeader />
      <div className="mx-auto max-w-2xl px-4 py-10 md:px-6">
        <h1 className="text-2xl font-semibold tracking-tight text-ink md:text-3xl">
          Tell us what you can finish
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-muted">
          A few filters plus free text. We’ll return a shortlist with one-sentence fit
          reasons.
        </p>

        <form onSubmit={onSubmit} className="mt-8 space-y-6">
          <label className="block">
            <span className="text-sm font-medium text-ink">Describe yourself</span>
            <textarea
              value={freeText}
              onChange={(e) => setFreeText(e.target.value)}
              rows={4}
              className="mt-1.5 w-full rounded-md border border-line px-3 py-2.5 text-sm outline-none focus:border-accent"
            />
          </label>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="text-sm font-medium text-ink">Name (optional)</span>
              <input
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Priya"
                className="mt-1.5 w-full rounded-md border border-line px-3 py-2.5 text-sm outline-none focus:border-accent"
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-ink">
                Email {alertsEnabled ? "(required for alerts)" : "(optional)"}
              </span>
              <input
                type="email"
                value={email}
                required={alertsEnabled}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="priya@college.edu"
                className="mt-1.5 w-full rounded-md border border-line px-3 py-2.5 text-sm outline-none focus:border-accent"
              />
            </label>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="text-sm font-medium text-ink">Skill level</span>
              <select
                value={skillLevel}
                onChange={(e) => setSkillLevel(e.target.value as SkillLevel)}
                className="mt-1.5 w-full rounded-md border border-line bg-white px-3 py-2.5 text-sm outline-none focus:border-accent"
              >
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </label>
            <label className="block">
              <span className="text-sm font-medium text-ink">Country</span>
              <select
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                className="mt-1.5 w-full rounded-md border border-line bg-white px-3 py-2.5 text-sm outline-none focus:border-accent"
              >
                <option value="IN">India</option>
                <option value="US">United States</option>
                <option value="GB">United Kingdom</option>
                <option value="SG">Singapore</option>
                <option value="GLOBAL">Global / Other</option>
              </select>
            </label>
          </div>

          <fieldset>
            <legend className="text-sm font-medium text-ink">Domains</legend>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {DOMAIN_OPTIONS.map((option) => {
                const active = domainSet.has(option.value);
                return (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => toggleDomain(option.value)}
                    className={`rounded border px-2.5 py-1 text-xs ${
                      active
                        ? "border-ink bg-ink text-white"
                        : "border-line text-muted hover:border-ink/30"
                    }`}
                  >
                    {option.label}
                  </button>
                );
              })}
            </div>
          </fieldset>

          <div className="grid gap-2 text-sm text-muted sm:grid-cols-2">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={preferStarter}
                onChange={(e) => setPreferStarter(e.target.checked)}
                className="size-3.5 accent-accent"
              />
              Prefer starter code
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={studentsOnlyOk}
                onChange={(e) => setStudentsOnlyOk(e.target.checked)}
                className="size-3.5 accent-accent"
              />
              Student-only events OK
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={canTravel}
                onChange={(e) => setCanTravel(e.target.checked)}
                className="size-3.5 accent-accent"
              />
              Can travel for in-person
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={alertsEnabled}
                onChange={(e) => setAlertsEnabled(e.target.checked)}
                className="size-3.5 accent-accent"
              />
              Email weekly matches
            </label>
          </div>

          {error && <p className="text-sm text-[var(--danger)]">{error}</p>}

          <div className="flex flex-wrap items-center gap-4">
            <button
              type="submit"
              disabled={pending || domains.length === 0}
              className="rounded-md bg-accent px-5 py-2.5 text-sm font-semibold text-white hover:bg-accent-hover disabled:opacity-60"
            >
              {pending ? "Matching…" : "Show my shortlist"}
            </button>
            <Link href="/" className="text-sm text-muted hover:text-ink">
              Back to competitions
            </Link>
          </div>
        </form>
      </div>
    </main>
  );
}

export default function OnboardingPage() {
  return (
    <Suspense
      fallback={
        <main className="grid min-h-screen place-items-center bg-white text-muted">
          Loading…
        </main>
      }
    >
      <OnboardingForm />
    </Suspense>
  );
}