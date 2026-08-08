import { Listing } from "@/lib/api";

const HORIZON_DAYS = 45;

export function daysUntil(iso?: string | null): number | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return Math.ceil((date.getTime() - Date.now()) / 86400000);
}

export function urgency(days: number | null): "" | "urgent" | "roomy" {
  if (days === null) return "";
  if (days <= 7) return "urgent";
  if (days >= 45) return "roomy";
  return "";
}

export function runwaySpent(days: number | null): number {
  if (days === null) return 40;
  const left = Math.max(0, Math.min(HORIZON_DAYS, days));
  return Math.max(0, Math.min(100, ((HORIZON_DAYS - left) / HORIZON_DAYS) * 100));
}

export function formatPrize(amount?: number | null): string {
  if (!amount) return "—";
  return `$${amount.toLocaleString()}`;
}

export function domainLabel(domain: string): string {
  const map: Record<string, string> = {
    "web-dev": "Web dev",
    mobile: "Mobile",
    nlp: "NLP",
    cv: "Computer vision",
    tabular: "Tabular ML",
    web3: "Web3",
    hardware: "Hardware",
    "game-dev": "Game dev",
    other: "Other",
  };
  return map[domain] || domain;
}

export function openInIndia(listing: Listing): boolean {
  const restrictions = listing.country_restrictions || [];
  if (!restrictions.length) return true;
  return restrictions.some((code) => code.toUpperCase() === "IN");
}

export function finishScore(listing: Listing): number {
  const days = daysUntil(listing.deadline_utc);
  if (days === null) return 50;
  let score = Math.min(days, 40);
  if (listing.has_starter_code) score += 12;
  if (listing.skill_floor === "beginner") score += 8;
  if (days < 5) score -= 20;
  return score;
}

export { HORIZON_DAYS };