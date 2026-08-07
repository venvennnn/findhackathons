import { Listing } from "@/lib/api";
import { daysUntil, formatDeadline } from "@/lib/utils";

export function ListingResult({ listing, index }: { listing: Listing; index: number }) {
  const days = daysUntil(listing.deadline_utc);

  return (
    <article
      className="group border-b border-[var(--line)] py-7 first:pt-0 last:border-b-0"
      style={{ animationDelay: `${index * 80}ms` }}
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-2xl">
          <div className="mb-2 flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.14em] text-mist">
            <span>{listing.source}</span>
            <span className="text-teal/70">•</span>
            <span>{listing.skill_floor}</span>
            {listing.has_starter_code && (
              <>
                <span className="text-teal/70">•</span>
                <span className="text-amber-soft">starter code</span>
              </>
            )}
            {listing.is_expanded_match && (
              <>
                <span className="text-teal/70">•</span>
                <span>expanded match</span>
              </>
            )}
          </div>
          <h3 className="display text-2xl font-bold leading-tight text-foam transition group-hover:text-teal-bright md:text-[1.7rem]">
            <a href={listing.url} target="_blank" rel="noreferrer">
              {listing.title}
            </a>
          </h3>
          <p className="mt-2 text-sm text-mist">
            {listing.organizer}
            {listing.prize_pool_usd
              ? ` · $${listing.prize_pool_usd.toLocaleString()} prize pool`
              : ""}
          </p>
          {listing.fit_reason && (
            <p className="mt-4 max-w-2xl text-[0.95rem] leading-relaxed text-foam/90">
              {listing.fit_reason}
            </p>
          )}
          <div className="mt-4 flex flex-wrap gap-2 text-xs text-mist">
            {listing.domains.map((domain) => (
              <span
                key={domain}
                className="rounded border border-[var(--line)] px-2 py-1"
              >
                {domain}
              </span>
            ))}
            {listing.students_only && (
              <span className="rounded border border-[var(--line)] px-2 py-1">
                students only
              </span>
            )}
            {listing.requires_travel && (
              <span className="rounded border border-[var(--line)] px-2 py-1">
                travel required
              </span>
            )}
          </div>
        </div>
        <div className="min-w-[9rem] text-right">
          <p className="text-xs uppercase tracking-[0.14em] text-mist">Deadline</p>
          <p className="mt-1 text-sm font-medium text-foam">
            {formatDeadline(listing.deadline_utc)}
          </p>
          {days !== null && (
            <p className="mt-1 text-xs text-teal-bright">
              {days > 0 ? `${days} days left` : "Closing soon"}
            </p>
          )}
          <a
            href={listing.url}
            target="_blank"
            rel="noreferrer"
            className="mt-4 inline-flex rounded-md bg-teal px-4 py-2 text-sm font-semibold text-ink transition hover:bg-teal-bright"
          >
            Open listing
          </a>
        </div>
      </div>
    </article>
  );
}