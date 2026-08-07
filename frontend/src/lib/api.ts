const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type SkillLevel = "beginner" | "intermediate" | "advanced";

export type DomainCategory =
  | "web-dev"
  | "mobile"
  | "nlp"
  | "cv"
  | "tabular"
  | "web3"
  | "hardware"
  | "game-dev"
  | "other";

export interface Listing {
  id: string;
  title: string;
  organizer: string;
  url: string;
  source: string;
  deadline_utc?: string | null;
  domains: DomainCategory[];
  skill_floor: SkillLevel;
  skill_floor_reasoning: string;
  students_only: boolean;
  country_restrictions: string[];
  team_size_max?: number | null;
  requires_travel: boolean;
  prize_pool_usd?: number | null;
  has_starter_code: boolean;
  confidence: string;
  is_active: boolean;
  fit_reason?: string | null;
  is_expanded_match?: boolean;
}

export interface MatchResponse {
  matches: Listing[];
  total_candidates: number;
  broadened: boolean;
  message?: string | null;
  suggest_alerts: boolean;
}

export interface ProfilePayload {
  email?: string;
  display_name?: string;
  free_text?: string;
  skill_level: SkillLevel;
  domains: DomainCategory[];
  country: string;
  students_only_ok: boolean;
  can_travel: boolean;
  prefer_starter_code: boolean;
  min_deadline_days: number;
  alerts_enabled: boolean;
}

export interface Profile extends ProfilePayload {
  id: string;
  created_at: string;
  updated_at: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function createProfile(payload: ProfilePayload) {
  return request<Profile>("/api/profiles", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function matchHackathons(payload: Record<string, unknown>) {
  return request<MatchResponse>("/api/match", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function subscribeAlerts(payload: {
  email: string;
  profile_id?: string;
  skill_level: SkillLevel;
  domains: DomainCategory[];
  country: string;
  free_text?: string;
}) {
  return request<{ ok: boolean; message: string; profile_id: string }>(
    "/api/alerts/subscribe",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function getListings(params?: Record<string, string>) {
  const query = params ? `?${new URLSearchParams(params)}` : "";
  return request<Listing[]>(`/api/listings${query}`);
}

export const DOMAIN_OPTIONS: { value: DomainCategory; label: string }[] = [
  { value: "web-dev", label: "Web Dev" },
  { value: "mobile", label: "Mobile" },
  { value: "nlp", label: "NLP" },
  { value: "cv", label: "Computer Vision" },
  { value: "tabular", label: "Tabular / Classic ML" },
  { value: "web3", label: "Web3" },
  { value: "hardware", label: "Hardware" },
  { value: "game-dev", label: "Game Dev" },
  { value: "other", label: "Other" },
];