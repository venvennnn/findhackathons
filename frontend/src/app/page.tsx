import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";

export default function HomePage() {
  return (
    <main className="grain min-h-screen overflow-hidden">
      <section className="relative min-h-screen">
        <div
          aria-hidden
          className="absolute inset-0 bg-cover bg-center"
          style={{
            backgroundImage:
              "url('https://images.unsplash.com/photo-1522071820081-009f0129c71c?auto=format&fit=crop&w=2000&q=80')",
          }}
        />
        <div
          aria-hidden
          className="absolute inset-0 bg-gradient-to-r from-[#061019]/94 via-[#07131f]/82 to-[#082029]/55"
        />
        <div
          aria-hidden
          className="hero-glow absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(47,212,200,0.22),transparent_40%),radial-gradient(circle_at_80%_10%,rgba(232,163,23,0.16),transparent_35%)]"
        />

        <div className="relative z-10 flex min-h-screen flex-col">
          <SiteHeader />
          <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col justify-end px-5 pb-16 pt-10 md:px-8 md:pb-24">
            <p className="fade-up display text-5xl font-extrabold tracking-tight text-foam sm:text-6xl md:text-7xl lg:text-8xl">
              FindHackathons
            </p>
            <h1 className="fade-up-delay mt-5 max-w-2xl text-2xl font-medium leading-snug text-foam md:text-3xl">
              Finishable competitions, matched to your skill — not just another link dump.
            </h1>
            <p className="fade-up-delay-2 mt-5 max-w-xl text-base leading-relaxed text-mist md:text-lg">
              Built for students and early-career builders in India and beyond.
              Shortlist 3–5 active hackathons you can actually ship.
            </p>
            <div className="fade-up-delay-2 mt-8 flex flex-wrap items-center gap-3">
              <Link
                href="/onboarding"
                className="rounded-md bg-amber px-6 py-3.5 text-sm font-semibold text-ink transition hover:bg-amber-soft"
              >
                Find my matches
              </Link>
              <Link
                href="/onboarding?mode=alerts"
                className="rounded-md border border-foam/25 bg-ink/30 px-6 py-3.5 text-sm font-medium text-foam backdrop-blur-sm transition hover:border-teal/50 hover:text-teal-bright"
              >
                Set up alerts
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="relative z-10 border-t border-[var(--line)] bg-[#061019]/90">
        <div className="mx-auto grid max-w-6xl gap-10 px-5 py-16 md:grid-cols-3 md:px-8">
          {[
            {
              title: "Structured metadata",
              body: "Domains, skill floor, travel rules, and student-only flags — extracted automatically.",
            },
            {
              title: "Beginner-first ranking",
              body: "Starter repos and finishable timelines surface first when you’re still building confidence.",
            },
            {
              title: "Alerts that retain",
              body: "When filters are too narrow today, we email you the moment a match opens.",
            },
          ].map((item) => (
            <div key={item.title}>
              <h2 className="display text-xl font-bold text-foam">{item.title}</h2>
              <p className="mt-3 text-sm leading-relaxed text-mist">{item.body}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}