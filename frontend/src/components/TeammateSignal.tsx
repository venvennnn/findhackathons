"use client";

import { FormEvent, useState } from "react";
import { Listing, expressListingInterest } from "@/lib/api";

const DISCORD_FALLBACK =
  "https://discord.com/channels/1535536397463724062/1535536398093000708";

export function TeammateSignal({
  listing,
  onInterest,
}: {
  listing: Listing;
  onInterest?: (count: number) => void;
}) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">(
    "idle",
  );
  const [message, setMessage] = useState("");
  const [discordUrl, setDiscordUrl] = useState(
    listing.team_channel_url || DISCORD_FALLBACK,
  );

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setStatus("loading");
    try {
      const result = await expressListingInterest(listing.id, { email });
      const nextDiscord = result.discord_url || DISCORD_FALLBACK;
      setMessage(result.message);
      setDiscordUrl(nextDiscord);
      setStatus("done");
      onInterest?.(result.interest_count);
      window.open(nextDiscord, "_blank", "noopener,noreferrer");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not save");
      setStatus("error");
    }
  }

  return (
    <div className="teammate">
      <div className="teammate-actions">
        {status === "done" ? (
          <a
            className="teammate-link"
            href={discordUrl}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
          >
            Open Discord → introduce yourself
          </a>
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
      {status === "done" && (
        <p className="teammate-hint">
          Mention <strong>{listing.title}</strong> in Discord so people know
          which competition you&apos;re joining.
        </p>
      )}
      {open && status !== "done" && (
        <form
          className="teammate-form"
          onSubmit={onSubmit}
          onClick={(e) => e.stopPropagation()}
        >
          <p className="teammate-hint">
            Drop your email for this competition, then we&apos;ll send you to
            Discord to introduce yourself.
          </p>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@college.edu"
            aria-label="Email for teammate interest"
          />
          <p className="teammate-comp">
            Competition: <span>{listing.title}</span>
          </p>
          <button type="submit" disabled={status === "loading"}>
            {status === "loading" ? "Saving…" : "Save & open Discord"}
          </button>
          {status === "error" && <p className="teammate-error">{message}</p>}
        </form>
      )}
    </div>
  );
}
