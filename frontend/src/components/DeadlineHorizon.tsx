"use client";

import { useMemo, useState } from "react";
import { Listing } from "@/lib/api";
import { HORIZON_DAYS, daysUntil, urgency } from "@/lib/utils";

export function DeadlineHorizon({ listings }: { listings: Listing[] }) {
  const [tip, setTip] = useState<{ text: string; left: string } | null>(null);

  const items = useMemo(() => {
    return listings
      .map((listing) => ({
        id: listing.id,
        title: listing.title,
        left: daysUntil(listing.deadline_utc),
      }))
      .filter((item) => item.left !== null && item.left >= 0)
      .map((item) => ({ ...item, left: item.left as number }))
      .sort((a, b) => a.left - b.left);
  }, [listings]);

  const urgentCount = items.filter((item) => item.left <= 7).length;
  const ticks = [0, 7, 14, 21, 28, 35];
  const lanes: number[] = [];

  return (
    <div className="horizon" aria-label="Deadline horizon for the next five weeks">
      <div className="horizon-head">
        <span>Deadline horizon</span>
        <span>
          <b>{urgentCount}</b> closing within 7 days
        </span>
      </div>
      <div className="track">
        <div className="axis" />
        {ticks.map((n) => (
          <div
            key={n}
            className={`tick${n === 0 ? " now" : ""}`}
            style={{ left: `${(n / HORIZON_DAYS) * 100}%` }}
          >
            <i />
            <u>{n === 0 ? "Today" : n === 35 ? "35d+" : `+${n}d`}</u>
          </div>
        ))}
        {tip && (
          <div className="pip-tip on" style={{ left: tip.left }}>
            {tip.text}
          </div>
        )}
        {items.map((item) => {
          const pct = (Math.min(item.left, HORIZON_DAYS) / HORIZON_DAYS) * 100;
          let lane = 0;
          while (lanes[lane] !== undefined && pct - lanes[lane] < 4.5) lane += 1;
          lanes[lane] = pct;
          const u = urgency(item.left);
          return (
            <button
              key={item.id}
              type="button"
              className={`pip ${u}`}
              data-lane={Math.min(lane, 3)}
              style={{ left: `${pct}%` }}
              aria-label={`${item.title} — closes in ${item.left} days`}
              onMouseEnter={() =>
                setTip({ text: `${item.title} · ${item.left}d`, left: `${pct}%` })
              }
              onFocus={() =>
                setTip({ text: `${item.title} · ${item.left}d`, left: `${pct}%` })
              }
              onMouseLeave={() => setTip(null)}
              onBlur={() => setTip(null)}
              onClick={() =>
                document.getElementById(`card-${item.id}`)?.scrollIntoView({
                  block: "center",
                  behavior: "smooth",
                })
              }
            />
          );
        })}
      </div>
    </div>
  );
}