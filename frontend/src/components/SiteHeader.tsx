import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="bg-white">
      <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-5 py-5">
        <Link href="/" className="text-base font-semibold tracking-tight text-ink">
          FindHackathons
        </Link>
        <Link
          href="/onboarding?mode=alerts"
          className="text-sm text-muted transition hover:text-ink"
        >
          Alerts
        </Link>
      </div>
    </header>
  );
}