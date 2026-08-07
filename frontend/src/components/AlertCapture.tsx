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
}

export function AlertCapture({
  skillLevel = "beginner",
  domains = [],
  country = "IN",
  freeText,
  profileId,
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
    <div className="border-t border-line pt-6">
      <h3 className="text-sm font-medium text-ink">Weekly alerts</h3>
      <p className="mt-1 text-sm text-muted">
        Get an email when something finishable opens.
      </p>
      {status === "done" ? (
        <p className="mt-3 text-sm text-ink">{message}</p>
      ) : (
        <form onSubmit={onSubmit} className="mt-3 flex gap-2">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            className="w-full border border-line bg-white px-3 py-2 text-sm outline-none focus:border-ink"
          />
          <button
            type="submit"
            disabled={status === "loading"}
            className="shrink-0 bg-ink px-3 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            {status === "loading" ? "…" : "Join"}
          </button>
        </form>
      )}
      {status === "error" && (
        <p className="mt-2 text-sm text-[var(--danger)]">{message}</p>
      )}
    </div>
  );
}