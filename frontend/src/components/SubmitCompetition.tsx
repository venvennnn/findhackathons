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
  const [organizer, setOrganizer] = useState("");
  const [deadline, setDeadline] = useState("");
  const [prize, setPrize] = useState("");
  const [skill, setSkill] = useState<SkillLevel>("intermediate");
  const [domains, setDomains] = useState<Set<DomainCategory>>(new Set());
  const [notes, setNotes] = useState("");
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">(
    "idle",
  );
  const [message, setMessage] = useState("");

  function toggleDomain(domain: DomainCategory) {
    setDomains((current) => {
      const next = new Set(current);
      if (next.has(domain)) next.delete(domain);
      else next.add(domain);
      return next;
    });
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setStatus("loading");
    try {
      const prizeNum = prize.trim() ? Number(prize.replace(/[,$]/g, "")) : null;
      const result = await submitCompetition({
        title,
        url,
        organizer: organizer || undefined,
        deadline_utc: deadline
          ? new Date(`${deadline}T23:59:00Z`).toISOString()
          : undefined,
        prize_pool_usd:
          prizeNum != null && !Number.isNaN(prizeNum) ? prizeNum : undefined,
        skill_floor: skill,
        domains: Array.from(domains),
        notes: notes || undefined,
        submitter_email: email || undefined,
      });
      setMessage(result.message);
      setStatus("done");
      setTitle("");
      setUrl("");
      setOrganizer("");
      setDeadline("");
      setPrize("");
      setNotes("");
      setDomains(new Set());
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not submit");
      setStatus("error");
    }
  }

  return (
    <section className="submit-comp" id="submit">
      <div className="wrap">
        <div>
          <h2>Missing a competition?</h2>
          <p>
            Add one we don&apos;t scrape yet, or correct a listing that looks
            wrong. It goes live for everyone right away, under its real site
            (Kaggle, Devpost, …), marked as added by someone.
          </p>
        </div>
        {status === "done" ? (
          <div>
            <p className="fineprint" style={{ color: "var(--moss)" }}>
              {message}
            </p>
            <button
              type="button"
              className="submit-again"
              onClick={() => setStatus("idle")}
            >
              Add another
            </button>
          </div>
        ) : (
          <form className="submit-form" onSubmit={onSubmit}>
            <label>
              Title
              <input
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="ARC Prize 2026"
              />
            </label>
            <label>
              Link
              <input
                required
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://…"
              />
            </label>
            <label>
              Organizer
              <input
                value={organizer}
                onChange={(e) => setOrganizer(e.target.value)}
                placeholder="Kaggle, college club, …"
              />
            </label>
            <div className="submit-row">
              <label>
                Deadline
                <input
                  type="date"
                  value={deadline}
                  onChange={(e) => setDeadline(e.target.value)}
                />
              </label>
              <label>
                Prize (USD)
                <input
                  inputMode="numeric"
                  value={prize}
                  onChange={(e) => setPrize(e.target.value)}
                  placeholder="25000"
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
            </div>
            <div className="team-needs" role="group" aria-label="Domains">
              {DOMAIN_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  className="chip"
                  aria-pressed={domains.has(option.value)}
                  onClick={() => toggleDomain(option.value)}
                >
                  {option.label}
                </button>
              ))}
            </div>
            <label>
              Notes (optional)
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Anything we should know — eligibility, Discord, starter kit…"
                rows={3}
              />
            </label>
            <label>
              Your email (optional)
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="so we can follow up if needed"
              />
            </label>
            <button type="submit" disabled={status === "loading"}>
              {status === "loading" ? "Saving…" : "Add competition"}
            </button>
            {status === "error" && (
              <p className="teammate-error">{message}</p>
            )}
          </form>
        )}
      </div>
    </section>
  );
}
