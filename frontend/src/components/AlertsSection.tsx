"use client";

import { FormEvent, useState } from "react";
import { DomainCategory, SkillLevel, subscribeAlerts } from "@/lib/api";

const DISCORD_URL =
  "https://discord.com/channels/1535536397463724062/1535536398093000708";

export function AlertsSection({
  skillLevel = "beginner",
  domains = [],
}: {
  skillLevel?: SkillLevel;
  domains?: DomainCategory[];
}) {
  const [email, setEmail] = useState("");
  const [lookingForTeam, setLookingForTeam] = useState(false);
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
        skill_level: skillLevel,
        domains,
        country: "IN",
        looking_for_team: lookingForTeam,
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
            <div>
              <p className="fineprint" style={{ color: "var(--moss)" }}>
                {message}
              </p>
              {lookingForTeam && (
                <p className="fineprint" style={{ marginTop: 10 }}>
                  <a
                    className="teammate-link"
                    href={DISCORD_URL}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open Discord → find teammates
                  </a>
                </p>
              )}
            </div>
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
                <span>
                  I&apos;m looking for teammates (we&apos;ll point you to
                  Discord)
                </span>
              </label>
            </form>
          )}
          {status === "error" ? (
            <p className="fineprint" style={{ color: "var(--coral)" }}>
              {message}
            </p>
          ) : (
            <p className="fineprint">
              No spam ·{" "}
              <a className="tlink" href="/unsubscribe">
                unsubscribe
              </a>{" "}
              in one click from any email
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
