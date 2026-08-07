"use client";

import { FormEvent, useState } from "react";
import {
  DomainCategory,
  SkillLevel,
  subscribeAlerts,
} from "@/lib/api";

interface AlertCaptureProps {
  skillLevel?: SkillLevel;
  domains?: DomainCategory[];
  country?: string;
  freeText?: string;
  profileId?: string;
  variant?: "banner" | "panel";
}

export function AlertCapture({
  skillLevel = "beginner",
  domains = [],
  country = "IN",
  freeText,
  profileId,
  variant = "panel",
}: AlertCaptureProps) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">(
    "idle",
  );
  const [message, setMessage] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setStatus("loading");
    try {
      const result = await subscribeAlerts({
        email,
        profile_id: profileId,
        skill_level: skillLevel,
        domains,
        country,
        free_text: freeText,
      });
      setMessage(result.message);
      setStatus("done");
    } catch {
      setMessage("Could not subscribe right now. Try again in a moment.");
      setStatus("error");
    }
  }

  if (variant === "banner") {
    return (
      <div className="bg-navy px-4 py-10 text-center text-white md:py-14">
        <h1 className="mx-auto max-w-3xl text-3xl font-semibold tracking-tight md:text-4xl">
          Discover hackathons & data science competitions
        </h1>
        <p className="mt-4 text-sm text-white/70">
          Sign up to the mailing list for weekly matches.
        </p>
        {status === "done" ? (
          <p className="mt-6 text-sm text-white/90">{message}</p>
        ) : (
          <form
            onSubmit={onSubmit}
            className="mx-auto mt-6 flex max-w-md flex-col gap-2 sm:flex-row"
          >
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email address"
              className="w-full rounded-md border-0 px-3 py-2.5 text-sm text-ink outline-none"
            />
            <button
              type="submit"
              disabled={status === "loading"}
              className="rounded-md bg-accent px-5 py-2.5 text-sm font-semibold text-white hover:bg-accent-hover disabled:opacity-60"
            >
              {status === "loading" ? "Saving…" : "Subscribe"}
            </button>
          </form>
        )}
        {status === "error" && (
          <p className="mt-3 text-sm text-red-300">{message}</p>
        )}
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-line bg-soft p-5">
      <h3 className="text-base font-semibold text-ink">Get weekly matches</h3>
      <p className="mt-1 text-sm text-muted">
        We’ll email you when finishable competitions open that match your filters.
      </p>
      {status === "done" ? (
        <p className="mt-4 text-sm text-link">{message}</p>
      ) : (
        <form onSubmit={onSubmit} className="mt-4 flex flex-col gap-2 sm:flex-row">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@college.edu"
            className="w-full rounded-md border border-line bg-white px-3 py-2.5 text-sm outline-none focus:border-accent"
          />
          <button
            type="submit"
            disabled={status === "loading"}
            className="rounded-md bg-accent px-4 py-2.5 text-sm font-semibold text-white hover:bg-accent-hover disabled:opacity-60"
          >
            {status === "loading" ? "Saving…" : "Subscribe"}
          </button>
        </form>
      )}
      {status === "error" && (
        <p className="mt-3 text-sm text-[var(--danger)]">{message}</p>
      )}
    </div>
  );
}