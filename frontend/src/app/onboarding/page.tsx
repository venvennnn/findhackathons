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
    <main className="grain min-h-screen">
      <div className="relative z-10">
        <SiteHeader />
        <div className="mx-auto max-w-3xl px-5 py-10 md:px-8 md:py-14">
          <p className="text-xs uppercase tracking-[0.18em] text-teal-bright">
            90-second onboarding
          </p>
          <h1 className="display mt-3 text-4xl font-extrabold tracking-tight text-foam md:text-5xl">
            Tell us what you can finish
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-relaxed text-mist">
            Mix free-text with a few filters. We’ll hard-filter deadlines and
            eligibility, then rank a shortlist with a one-sentence fit reason.
          </p>

          <form onSubmit={onSubmit} className="mt-10 space-y-8">
            <label className="block">
              <span className="text-sm font-medium text-foam">Describe yourself</span>
              <textarea
                value={freeText}
                onChange={(e) => setFreeText(e.target.value)}
                rows={4}
                className="mt-2 w-full rounded-md border border-[var(--line)] bg-ink/35 px-4 py-3 text-sm text-foam outline-none ring-teal/40 focus:ring-2"
              />
            </label>

            <div className="grid gap-5 md:grid-cols-2">
              <label className="block">
                <span className="text-sm font-medium text-foam">Name (optional)</span>
                <input
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Priya"
                  className="mt-2 w-full rounded-md border border-[var(--line)] bg-ink/35 px-4 py-3 text-sm text-foam outline-none ring-teal/40 focus:ring-2"
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-foam">
                  Email {alertsEnabled ? "(required for alerts)" : "(optional)"}
                </span>
                <input
                  type="email"
                  value={email}
                  required={alertsEnabled}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="priya@college.edu"
                  className="mt-2 w-full rounded-md border border-[var(--line)] bg-ink/35 px-4 py-3 text-sm text-foam outline-none ring-teal/40 focus:ring-2"
                />
              </label>
            </div>

            <div className="grid gap-5 md:grid-cols-2">
              <label className="block">
                <span className="text-sm font-medium text-foam">Skill level</span>
                <select
                  value={skillLevel}
                  onChange={(e) => setSkillLevel(e.target.value as SkillLevel)}
                  className="mt-2 w-full rounded-md border border-[var(--line)] bg-ink/35 px-4 py-3 text-sm text-foam outline-none ring-teal/40 focus:ring-2"
                >
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                </select>
              </label>
              <label className="block">
                <span className="text-sm font-medium text-foam">Country</span>
                <select
                  value={country}
                  onChange={(e) => setCountry(e.target.value)}
                  className="mt-2 w-full rounded-md border border-[var(--line)] bg-ink/35 px-4 py-3 text-sm text-foam outline-none ring-teal/40 focus:ring-2"
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
              <legend className="text-sm font-medium text-foam">Domains</legend>
              <div className="mt-3 flex flex-wrap gap-2">
                {DOMAIN_OPTIONS.map((option) => {
                  const active = domainSet.has(option.value);
                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => toggleDomain(option.value)}
                      className={`rounded-md border px-3 py-2 text-sm transition ${
                        active
                          ? "border-teal bg-teal/20 text-teal-bright"
                          : "border-[var(--line)] text-mist hover:border-mist/40 hover:text-foam"
                      }`}
                    >
                      {option.label}
                    </button>
                  );
                })}
              </div>
            </fieldset>

            <div className="grid gap-3 text-sm text-mist md:grid-cols-2">
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={preferStarter}
                  onChange={(e) => setPreferStarter(e.target.checked)}
                  className="size-4 accent-teal"
                />
                Prefer competitions with starter code
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={studentsOnlyOk}
                  onChange={(e) => setStudentsOnlyOk(e.target.checked)}
                  className="size-4 accent-teal"
                />
                Student-only events are OK
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={canTravel}
                  onChange={(e) => setCanTravel(e.target.checked)}
                  className="size-4 accent-teal"
                />
                I can travel for in-person events
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={alertsEnabled}
                  onChange={(e) => setAlertsEnabled(e.target.checked)}
                  className="size-4 accent-teal"
                />
                Email me weekly when matches open
              </label>
            </div>

            {error && <p className="text-sm text-[var(--danger)]">{error}</p>}

            <div className="flex flex-wrap items-center gap-3">
              <button
                type="submit"
                disabled={pending || domains.length === 0}
                className="rounded-md bg-amber px-6 py-3.5 text-sm font-semibold text-ink transition hover:bg-amber-soft disabled:opacity-60"
              >
                {pending ? "Matching…" : "Show my shortlist"}
              </button>
              <Link href="/" className="text-sm text-mist hover:text-foam">
                Back to home
              </Link>
            </div>
          </form>
        </div>
      </div>
    </main>
  );
}

export default function OnboardingPage() {
  return (
    <Suspense
      fallback={
        <main className="grid min-h-screen place-items-center text-mist">
          Loading onboarding…
        </main>
      }
    >
      <OnboardingForm />
    </Suspense>
  );
}