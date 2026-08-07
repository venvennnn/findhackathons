"use client";

import { FormEvent, useState } from "react";
import {
  DomainCategory,
  SkillLevel,
  subscribeAlerts,
} from "@/lib/api";

interface AlertCaptureProps {
  skillLevel: SkillLevel;
  domains: DomainCategory[];
  country: string;
  freeText?: string;
  profileId?: string;
  compact?: boolean;
}

export function AlertCapture({
  skillLevel,
  domains,
  country,
  freeText,
  profileId,
  compact = false,
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

  return (
    <div
      className={
        compact
          ? "border-t border-[var(--line)] pt-5"
          : "rounded-2xl border border-[var(--line)] bg-white/[0.03] p-6"
      }
    >
      <h3 className="display text-xl font-bold text-foam">
        Get weekly matches by email
      </h3>
      <p className="mt-2 max-w-xl text-sm leading-relaxed text-mist">
        Narrow searches often return nothing today. Alerts convert dead queries
        into notifications when a finishable competition opens.
      </p>
      {status === "done" ? (
        <p className="mt-4 text-sm text-teal-bright">{message}</p>
      ) : (
        <form
          onSubmit={onSubmit}
          className="mt-4 flex flex-col gap-3 sm:flex-row"
        >
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@college.edu"
            className="w-full rounded-md border border-[var(--line)] bg-ink/40 px-4 py-3 text-sm text-foam outline-none ring-teal/40 placeholder:text-mist/60 focus:ring-2"
          />
          <button
            type="submit"
            disabled={status === "loading"}
            className="whitespace-nowrap rounded-md bg-amber px-5 py-3 text-sm font-semibold text-ink transition hover:bg-amber-soft disabled:opacity-60"
          >
            {status === "loading" ? "Saving…" : "Join alerts"}
          </button>
        </form>
      )}
      {status === "error" && (
        <p className="mt-3 text-sm text-[var(--danger)]">{message}</p>
      )}
    </div>
  );
}