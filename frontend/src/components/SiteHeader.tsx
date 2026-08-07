import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="relative z-20 mx-auto flex w-full max-w-6xl items-center justify-between px-5 py-5 md:px-8">
      <Link href="/" className="display text-lg font-extrabold tracking-tight md:text-xl">
        Find<span className="text-teal-bright">Hackathons</span>
      </Link>
      <nav className="flex items-center gap-4 text-sm text-mist">
        <Link href="/onboarding" className="transition hover:text-foam">
          Find matches
        </Link>
        <Link
          href="/onboarding"
          className="rounded-md bg-teal px-3.5 py-2 font-medium text-ink transition hover:bg-teal-bright"
        >
          Start free
        </Link>
      </nav>
    </header>
  );
}