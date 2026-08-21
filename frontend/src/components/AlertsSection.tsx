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
    <section className="band" id="alerts">
      <div className="wrap inner">
        <h2>One email. Friday morning.</h2>
        <p className="sub">
          Five to eight competitions that match your level and close inside a
          month. Nothing else, ever.
        </p>
        {status === "done" ? (
          <div>
            <p className="note ok">{message}</p>
            {lookingForTeam && (
              <p className="note" style={{ marginTop: 10 }}>
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
          <form onSubmit={onSubmit}>
            <div className="inline">
              <label className="sr" htmlFor="alert-email">
                Your email
              </label>
              <input
                id="alert-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@college.edu"
              />
              <button type="submit" className="btn" disabled={status === "loading"}>
                {status === "loading" ? "Saving…" : "Get Friday's list"}
              </button>
            </div>
            <label className="team-check">
              <input
                type="checkbox"
                checked={lookingForTeam}
                onChange={(e) => setLookingForTeam(e.target.checked)}
              />
              <span>
                I&apos;m looking for teammates (we&apos;ll point you to Discord)
              </span>
            </label>
          </form>
        )}
        {status === "error" ? (
          <p className="note" style={{ color: "var(--urgent)" }}>
            {message}
          </p>
        ) : (
          <p className="note">
            No spam.{" "}
            <a href="/unsubscribe">Unsubscribe</a> in one click from any email.
          </p>
        )}
      </div>
    </section>
  );
}
