import { Listing } from "@/lib/api";
import { daysUntil, formatDeadline } from "@/lib/utils";

function deadlineLabel(iso?: string | null): string {
  const days = daysUntil(iso);
  if (days === null) return "Rolling";
  if (days <= 0) return "Closing soon";
  if (days < 30) return `${days} day${days === 1 ? "" : "s"} to go`;
  const months = Math.round(days / 30);
  return `${months} month${months === 1 ? "" : "s"} to go`;
}

export function ListingResult({ listing }: { listing: Listing; index?: number }) {
  return (
    <article className="border-b border-line py-5 first:pt-0">
      <div className="flex items-start justify-between gap-6">
        <div className="min-w-0 flex-1">
          <a
            href={listing.url}
            target="_blank"
            rel="noreferrer"
            className="text-[17px] font-semibold text-link underline-offset-2 hover:underline"
          >
            {listing.title}
          </a>
          <p className="mt-1 text-sm text-muted">{listing.organizer}</p>

          <div className="mt-3 flex flex-wrap gap-1.5">
            <span className="rounded border border-line px-2 py-0.5 text-xs text-muted">
              {listing.source}
            </span>
            <span className="rounded border border-line px-2 py-0.5 text-xs text-muted">
              {listing.skill_floor}
            </span>
            {listing.domains.map((domain) => (
              <span
                key={domain}
                className="rounded border border-line px-2 py-0.5 text-xs text-muted"
              >
                {domain}
              </span>
            ))}
            {listing.has_starter_code && (
              <span className="rounded border border-line px-2 py-0.5 text-xs text-muted">
                starter code
              </span>
            )}
            {listing.students_only && (
              <span className="rounded border border-line px-2 py-0.5 text-xs text-muted">
                students
              </span>
            )}
            {listing.is_expanded_match && (
              <span className="rounded border border-line px-2 py-0.5 text-xs text-muted">
                expanded match
              </span>
            )}
          </div>

          {listing.fit_reason && (
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted">
              {listing.fit_reason}
            </p>
          )}
        </div>

        <div className="shrink-0 text-right">
          <p className="text-sm font-semibold text-ink">
            {listing.prize_pool_usd
              ? `$${listing.prize_pool_usd.toLocaleString()}`
              : "—"}
          </p>
          <p className="mt-1 text-[11px] font-medium uppercase tracking-wide text-faint">
            {deadlineLabel(listing.deadline_utc)}
          </p>
          <p className="mt-1 text-xs text-faint">{formatDeadline(listing.deadline_utc)}</p>
        </div>
      </div>
    </article>
  );
}