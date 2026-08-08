"use client";

import { FormEvent, useState } from "react";
import {
  Listing,
  TEAM_ROLE_OPTIONS,
  TeamRole,
  expressListingInterest,
} from "@/lib/api";

export function TeammateSignal({
  listing,
  onRecorded,
}: {
  listing: Listing;
  onRecorded?: (listingId: string, count: number, isPublic: boolean) => void;
}) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [needs, setNeeds] = useState<Set<TeamRole>>(new Set());
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">(
    "idle",
  );
  const [message, setMessage] = useState("");

  function toggleNeed(role: TeamRole) {
    setNeeds((current) => {
      const next = new Set(current);
      if (next.has(role)) next.delete(role);
      else next.add(role);
      return next;
    });
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setStatus("loading");
    try {
      const result = await expressListingInterest(listing.id, {
        email,
        team_needs: Array.from(needs),
      });
      setMessage(result.message);
      setStatus("done");
      onRecorded?.(listing.id, result.interest_count, result.count_is_public);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not save");
      setStatus("error");
    }
  }

  const ambient = listing.teammate_interest_count;

  return (
    <div className="teammate">
      {ambient != null && ambient > 0 && (
        <p className="teammate-ambient">
          {ambient} people are looking for teammates for this one
        </p>
      )}
      <div className="teammate-actions">
        {listing.team_channel_url && (
          <a
            className="teammate-link"
            href={listing.team_channel_url}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
          >
            Event team channel
          </a>
        )}
        {status === "done" ? (
          <span className="teammate-done">Noted — kept private</span>
        ) : (
          <button
            type="button"
            className="teammate-btn"
            aria-expanded={open}
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setOpen((value) => !value);
            }}
          >
            Looking for teammates
          </button>
        )}
      </div>
      {open && status !== "done" && (
        <form
          className="teammate-form"
          onSubmit={onSubmit}
          onClick={(e) => e.stopPropagation()}
        >
          <p className="teammate-hint">
            We&apos;ll count your interest. No name or email is shown publicly.
          </p>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@college.edu"
            aria-label="Email for teammate interest"
          />
          <div className="team-needs" role="group" aria-label="Roles wanted">
            {TEAM_ROLE_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                className="chip"
                aria-pressed={needs.has(option.value)}
                onClick={() => toggleNeed(option.value)}
              >
                {option.label}
              </button>
            ))}
          </div>
          <button type="submit" disabled={status === "loading"}>
            {status === "loading" ? "Saving…" : "Count me in"}
          </button>
          {status === "error" && <p className="teammate-error">{message}</p>}
        </form>
      )}
    </div>
  );
}
