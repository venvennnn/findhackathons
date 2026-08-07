import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="border-b border-line bg-white">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-4 py-3 md:px-6">
        <Link href="/" className="text-[15px] font-semibold tracking-tight text-ink">
          FindHackathons
        </Link>
        <nav className="flex items-center gap-5 text-sm text-muted">
          <Link href="/" className="hover:text-ink">
            Competitions
          </Link>
          <Link href="/onboarding" className="hover:text-ink">
            Match me
          </Link>
          <Link
            href="/onboarding?mode=alerts"
            className="hidden text-ink hover:text-link sm:inline"
          >
            Get alerts →
          </Link>
        </nav>
      </div>
    </header>
  );
}