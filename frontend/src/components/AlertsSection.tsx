"use client";

import { FormEvent, useState } from "react";
import { DomainCategory, SkillLevel, subscribeAlerts } from "@/lib/api";

export function AlertsSection({
  skillLevel = "beginner",
  domains = [],
}: {
  skillLevel?: SkillLevel;
  domains?: DomainCategory[];
}) {
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
        skill_level: skillLevel,
        domains,
        country: "IN",
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
            </form>
          )}
          {status === "error" ? (
            <p className="fineprint" style={{ color: "var(--coral)" }}>
              {message}
            </p>
          ) : (
            <p className="fineprint">No spam · unsubscribe in one click</p>
          )}
        </div>
      </div>
    </section>
  );
}