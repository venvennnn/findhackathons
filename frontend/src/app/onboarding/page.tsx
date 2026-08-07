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
      <div className="mx-auto max-w-xl px-5 py-10">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">
          Match me
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-muted">
          Short preferences in, ranked shortlist out.
        </p>

        <form onSubmit={onSubmit} className="mt-8 space-y-6">
          <label className="block">
            <span className="text-sm text-ink">About you</span>
            <textarea
              value={freeText}
              onChange={(e) => setFreeText(e.target.value)}
              rows={4}
              className="mt-1.5 w-full border border-line px-3 py-2.5 text-sm outline-none focus:border-ink"
            />
          </label>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="text-sm text-ink">Name</span>
              <input
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Optional"
                className="mt-1.5 w-full border border-line px-3 py-2.5 text-sm outline-none focus:border-ink"
              />
            </label>
            <label className="block">
              <span className="text-sm text-ink">Email</span>
              <input
                type="email"
                value={email}
                required={alertsEnabled}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={alertsEnabled ? "Required for alerts" : "Optional"}
                className="mt-1.5 w-full border border-line px-3 py-2.5 text-sm outline-none focus:border-ink"
              />
            </label>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="text-sm text-ink">Skill</span>
              <select
                value={skillLevel}
                onChange={(e) => setSkillLevel(e.target.value as SkillLevel)}
                className="mt-1.5 w-full border border-line bg-white px-3 py-2.5 text-sm outline-none focus:border-ink"
              >
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </label>
            <label className="block">
              <span className="text-sm text-ink">Country</span>
              <select
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                className="mt-1.5 w-full border border-line bg-white px-3 py-2.5 text-sm outline-none focus:border-ink"
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
            <legend className="text-sm text-ink">Domains</legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {DOMAIN_OPTIONS.map((option) => {
                const active = domainSet.has(option.value);
                return (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => toggleDomain(option.value)}
                    className={`px-2.5 py-1 text-sm ${
                      active ? "bg-ink text-white" : "text-muted hover:text-ink"
                    }`}
                  >
                    {option.label}
                  </button>
                );
              })}
            </div>
          </fieldset>

          <div className="space-y-2 text-sm text-muted">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={preferStarter}
                onChange={(e) => setPreferStarter(e.target.checked)}
                className="size-3.5"
              />
              Prefer starter code
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={studentsOnlyOk}
                onChange={(e) => setStudentsOnlyOk(e.target.checked)}
                className="size-3.5"
              />
              Student-only events OK
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={canTravel}
                onChange={(e) => setCanTravel(e.target.checked)}
                className="size-3.5"
              />
              Can travel
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={alertsEnabled}
                onChange={(e) => setAlertsEnabled(e.target.checked)}
                className="size-3.5"
              />
              Email weekly matches
            </label>
          </div>

          {error && <p className="text-sm text-[var(--danger)]">{error}</p>}

          <div className="flex items-center gap-4">
            <button
              type="submit"
              disabled={pending || domains.length === 0}
              className="bg-ink px-4 py-2.5 text-sm font-medium text-white disabled:opacity-60"
            >
              {pending ? "Matching…" : "Show shortlist"}
            </button>
            <Link href="/" className="text-sm text-muted hover:text-ink">
              Cancel
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