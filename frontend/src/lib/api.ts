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

export type TeamRole =
  | "frontend"
  | "backend"
  | "ml"
  | "design"
  | "product"
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
  /** Event-run Discord / Devpost team channel. */
  team_channel_url?: string | null;
  /** Ambient demand — only present once count clears the server threshold. */
  teammate_interest_count?: number | null;
  /** True when someone added/corrected this listing via the public form. */
  community_submitted?: boolean;
  /** When the listing was first added to our feed (used for launch-date sort). */
  created_at?: string | null;
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
  looking_for_team?: boolean;
  team_needs?: TeamRole[];
}

export interface Profile extends ProfilePayload {
  id: string;
  created_at: string;
  updated_at: string;
}

function friendlyError(status: number, text: string): string {
  const trimmed = text.trim();
  if (
    trimmed.startsWith("<!DOCTYPE") ||
    trimmed.startsWith("<html") ||
    trimmed.includes("This page could not be found")
  ) {
    return (
      "API not reachable (got an HTML 404). On Vercel, set BACKEND_URL to your Railway URL " +
      "(e.g. https://your-app.up.railway.app) and redeploy."
    );
  }
  try {
    const parsed = JSON.parse(trimmed) as { detail?: string; message?: string };
    if (parsed.detail) return String(parsed.detail);
    if (parsed.message) return String(parsed.message);
  } catch {
    // not JSON
  }
  if (trimmed.length > 180) {
    return `Request failed (${status}). Check BACKEND_URL / Railway health.`;
  }
  return trimmed || `Request failed (${status})`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(friendlyError(response.status, text));
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
  looking_for_team?: boolean;
  team_needs?: TeamRole[];
}) {
  return request<{ ok: boolean; message: string; profile_id: string }>(
    "/api/alerts/subscribe",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function unsubscribeAlerts(token: string) {
  return request<{ ok: boolean; message: string }>("/api/alerts/unsubscribe", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}

export function expressListingInterest(
  listingId: string,
  payload: { email: string; team_needs?: TeamRole[]; profile_id?: string },
) {
  return request<{
    ok: boolean;
    message: string;
    listing_id: string;
    listing_title: string;
    interest_count: number;
    count_is_public: boolean;
    discord_url: string;
  }>(`/api/listings/${listingId}/interest`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function submitCompetition(payload: {
  title: string;
  url: string;
  organizer?: string;
  deadline_utc?: string;
  prize_pool_usd?: number;
  domains?: DomainCategory[];
  skill_floor?: SkillLevel;
  has_starter_code?: boolean;
  students_only?: boolean;
  requires_travel?: boolean;
  team_size_max?: number;
  notes?: string;
  submitter_email?: string;
}) {
  return request<{ ok: boolean; message: string; id: string; status: string }>(
    "/api/listings/submit",
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

export type SourcePlatform =
  | "kaggle"
  | "devpost"
  | "devfolio"
  | "unstop"
  | "manual"
  | "other";

export interface SourceCount {
  source: SourcePlatform;
  label: string;
  count: number;
  in_default_feed: boolean;
}

export interface SourcesResponse {
  sources: SourceCount[];
  default_sources: SourcePlatform[];
}

export function getSources() {
  return request<SourcesResponse>("/api/sources");
}

/** Default directory feed — Unstop is opt-in. */
export const DEFAULT_FEED_SOURCES: SourcePlatform[] = [
  "kaggle",
  "devpost",
  "devfolio",
  "other",
  "manual",
];

export function sourcesParam(sources: SourcePlatform[]): string {
  return sources.join(",");
}

export const TEAM_ROLE_OPTIONS: { value: TeamRole; label: string }[] = [
  { value: "frontend", label: "Frontend" },
  { value: "backend", label: "Backend" },
  { value: "ml", label: "ML / DS" },
  { value: "design", label: "Design" },
  { value: "product", label: "Product" },
  { value: "other", label: "Other" },
];

export const DOMAIN_OPTIONS: { value: DomainCategory; label: string }[] = [
  { value: "web-dev", label: "Web Dev" },
  { value: "tabular", label: "Tabular ML" },
  { value: "nlp", label: "NLP" },
  { value: "cv", label: "Computer Vision" },
  { value: "mobile", label: "Mobile" },
  { value: "hardware", label: "Hardware" },
  { value: "game-dev", label: "Game Dev" },
  { value: "web3", label: "Web3" },
  { value: "other", label: "Other" },
];

export const MATCH_EXAMPLES = [
  {
    label: "A student exploring data science",
    text: "Final-year student, decent at Python and pandas, no ML competitions yet. Looking for something tabular with starter code I can finish alone.",
  },
  {
    label: "A credit risk DS moving into NLP",
    text: "Credit risk data scientist, four years of tabular modelling, moving into NLP. Want something that stretches me.",
  },
  {
    label: "A frontend dev building a portfolio",
    text: "Frontend dev, React and Tailwind, building a portfolio. Happy to team up. Prize doesn't matter much.",
  },
];

/** Lightweight client-side read of free text for filters + match payload. */
export function inferProfile(text: string): {
  skill_level: SkillLevel;
  domains: DomainCategory[];
  prefer_starter_code: boolean;
} {
  const t = ` ${text.toLowerCase()} `;
  let skill_level: SkillLevel = "intermediate";
  if (
    /(never|first|just start|getting into|exploring|beginner|tutorial|new to|student)/.test(
      t,
    )
  ) {
    skill_level = "beginner";
  }
  if (
    /(years|senior|professional|scientist|production|phd|competitive)/.test(t)
  ) {
    skill_level = "advanced";
  }

  const domains: DomainCategory[] = [];
  const hints: [DomainCategory, RegExp][] = [
    ["tabular", /(credit|risk|tabular|xgboost|boosting|forecast|kaggle|churn)/],
    ["nlp", /(nlp|llm|language|text|agent|chatbot|rag|speech|voice)/],
    ["cv", /(vision|image|\bcv\b|segmentation|opencv|satellite)/],
    ["web-dev", /(web|frontend|react|next|javascript|fullstack|api|backend)/],
    ["mobile", /(mobile|android|ios|flutter)/],
    ["hardware", /(hardware|iot|embedded|arduino|raspberry)/],
    ["game-dev", /(game|godot|unity|gamedev)/],
    ["web3", /(web3|solidity|crypto|blockchain)/],
  ];
  for (const [domain, re] of hints) {
    if (re.test(t)) domains.push(domain);
  }
  if (!domains.length) domains.push("web-dev", "tabular");

  return {
    skill_level,
    domains,
    prefer_starter_code: skill_level === "beginner" || /starter|beginner/.test(t),
  };
}