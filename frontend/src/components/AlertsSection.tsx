"use client";

import { FormEvent, useState } from "react";
import {
  DomainCategory,
  SkillLevel,
  TEAM_ROLE_OPTIONS,
  TeamRole,
  subscribeAlerts,
} from "@/lib/api";

export function AlertsSection({
  skillLevel = "beginner",
  domains = [],
}: {
  skillLevel?: SkillLevel;
  domains?: DomainCategory[];
}) {
  const [email, setEmail] = useState("");
  const [lookingForTeam, setLookingForTeam] = useState(false);
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
      const result = await subscribeAlerts({
        email,
        skill_level: skillLevel,
        domains,
        country: "IN",
        looking_for_team: lookingForTeam,
        team_needs: lookingForTeam ? Array.from(needs) : [],
      });
      setMessage(result.message);
      setStatus("done");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not subscribe");
      setStatus("error");
    }
  }

  return (
    <section className="alerts" id="alerts">
      <div className="wrap">
        <div>
          <h2>One email. Friday morning.</h2>
          <p>
            Five to eight hackathons that match your level and close in the next
            month. Nothing else.
          </p>
        </div>
        <div>
          {status === "done" ? (
            <p className="fineprint" style={{ color: "var(--moss)" }}>
              {message}
            </p>
          ) : (
            <form className="form" onSubmit={onSubmit}>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@college.edu"
                aria-label="Email address"
              />
              <button type="submit" disabled={status === "loading"}>
                {status === "loading" ? "Saving…" : "Get Friday's list"}
              </button>
              <label className="team-check">
                <input
                  type="checkbox"
                  checked={lookingForTeam}
                  onChange={(e) => setLookingForTeam(e.target.checked)}
                />
                <span>I&apos;m also looking for teammates</span>
              </label>
              {lookingForTeam && (
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
              )}
            </form>
          )}
          {status === "error" ? (
            <p className="fineprint" style={{ color: "var(--coral)" }}>
              {message}
            </p>
          ) : (
            <p className="fineprint">
              No spam · teammate intent stays private · unsubscribe in one click
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
