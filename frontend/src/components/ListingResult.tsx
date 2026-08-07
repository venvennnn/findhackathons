import { Listing } from "@/lib/api";
import { daysUntil, formatDeadline } from "@/lib/utils";

function remaining(iso?: string | null): string {
  const days = daysUntil(iso);
  if (days === null) return "Rolling deadline";
  if (days <= 0) return "Closing soon";
  if (days === 1) return "1 day left";
  return `${days} days left`;
}

export function ListingResult({ listing }: { listing: Listing; index?: number }) {
  const meta = [
    listing.source,
    listing.skill_floor,
    ...listing.domains.slice(0, 2),
    listing.has_starter_code ? "starter code" : null,
  ].filter(Boolean);

  return (
    <article className="py-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-baseline sm:justify-between sm:gap-8">
        <div className="min-w-0">
          <a
            href={listing.url}
            target="_blank"
            rel="noreferrer"
            className="text-lg font-medium text-ink underline-offset-4 hover:underline"
          >
            {listing.title}
          </a>
          <p className="mt-1 text-sm text-muted">{listing.organizer}</p>
          {listing.fit_reason && (
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted">
              {listing.fit_reason}
            </p>
          )}
          <p className="mt-3 text-xs text-faint">{meta.join(" · ")}</p>
        </div>
        <div className="shrink-0 text-sm text-muted sm:text-right">
          <p>{remaining(listing.deadline_utc)}</p>
          <p className="mt-0.5 text-xs text-faint">
            {formatDeadline(listing.deadline_utc)}
            {listing.prize_pool_usd
              ? ` · $${listing.prize_pool_usd.toLocaleString()}`
              : ""}
          </p>
        </div>
      </div>
    </article>
  );
}