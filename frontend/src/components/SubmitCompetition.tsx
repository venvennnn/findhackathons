"use client";

import { FormEvent, useState } from "react";
import {
  DOMAIN_OPTIONS,
  DomainCategory,
  SkillLevel,
  submitCompetition,
} from "@/lib/api";

export function SubmitCompetition() {
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [deadline, setDeadline] = useState("");
  const [prize, setPrize] = useState("");
  const [skill, setSkill] = useState<SkillLevel>("intermediate");
  const [domain, setDomain] = useState<DomainCategory>("tabular");
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">(
    "idle",
  );
  const [message, setMessage] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setStatus("loading");
    try {
      const prizeNum = prize.trim() ? Number(prize.replace(/[,$]/g, "")) : null;
      const result = await submitCompetition({
        title,
        url,
        deadline_utc: deadline
          ? new Date(`${deadline}T23:59:00Z`).toISOString()
          : undefined,
        prize_pool_usd:
          prizeNum != null && !Number.isNaN(prizeNum) ? prizeNum : undefined,
        skill_floor: skill,
        domains: [domain],
      });
      setMessage(result.message);
      setStatus("done");
      setTitle("");
      setUrl("");
      setDeadline("");
      setPrize("");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not submit");
      setStatus("error");
    }
  }

  return (
    <section className="band" id="submit">
      <div className="wrap inner">
        <h2>Missing a competition?</h2>
        <p className="sub">
          Add one we don&apos;t scrape yet, or fix a listing that looks wrong. It
          goes live immediately under its real host, tagged as community-added.
        </p>
        {status === "done" ? (
          <div>
            <p className="note ok">{message}</p>
            <p style={{ marginTop: 20 }}>
              <button
                type="button"
                className="btn quiet"
                onClick={() => setStatus("idle")}
              >
                Add another
              </button>
            </p>
          </div>
        ) : (
          <form className="form" onSubmit={onSubmit}>
            <label className="full">
              Title
              <input
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Winter tabular playground"
              />
            </label>
            <label className="full">
              Link
              <input
                required
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://kaggle.com/competitions/..."
              />
            </label>
            <label>
              Deadline
              <input
                type="date"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
              />
            </label>
            <label>
              Prize in USD
              <input
                inputMode="numeric"
                value={prize}
                onChange={(e) => setPrize(e.target.value)}
                placeholder="0"
              />
            </label>
            <label>
              Skill floor
              <select
                value={skill}
                onChange={(e) => setSkill(e.target.value as SkillLevel)}
              >
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </label>
            <label>
              Track
              <select
                value={domain}
                onChange={(e) => setDomain(e.target.value as DomainCategory)}
              >
                {DOMAIN_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <p className="full" style={{ marginTop: 8 }}>
              <button type="submit" className="btn quiet" disabled={status === "loading"}>
                {status === "loading" ? "Saving…" : "Add competition"}
              </button>
            </p>
            {status === "error" && (
              <p className="full teammate-error">{message}</p>
            )}
          </form>
        )}
      </div>
    </section>
  );
}
