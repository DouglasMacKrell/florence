const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type IntakeRecord = Record<string, unknown>;

export type SessionMessage = {
  role: string;
  content: string;
  created_at?: string;
};

export type MatchResult = {
  provider_id: string;
  score: number;
  rank: number;
  strengths: string[];
  concerns: string[];
};

export type SessionDetail = {
  session_id: string;
  state: string;
  status: string;
  intake: IntakeRecord;
  completion_percent: number;
  messages: SessionMessage[];
  matches: MatchResult[];
  care_recommendation?: {
    primary: string;
    alternatives: string[];
    rationale: string;
  };
  referral?: {
    provider_id: string;
    status: string;
  };
};

export async function createSession(): Promise<{ session_id: string; greeting: string; state: string }> {
  const response = await fetch(`${API_BASE}/sessions`, { method: "POST" });
  if (!response.ok) {
    throw new Error("Failed to create session");
  }
  return response.json();
}

export async function sendMessage(
  sessionId: string,
  content: string,
): Promise<{
  content: string;
  state: string;
  intake: IntakeRecord;
  matches?: MatchResult[];
  care_recommendation?: SessionDetail["care_recommendation"];
}> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (!response.ok) {
    throw new Error("Failed to send message");
  }
  return response.json();
}

export async function getSession(sessionId: string): Promise<SessionDetail> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}`);
  if (!response.ok) {
    throw new Error("Failed to load session");
  }
  return response.json();
}

export async function selectProvider(sessionId: string, providerId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/select-provider`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider_id: providerId }),
  });
  if (!response.ok) {
    throw new Error("Failed to select provider");
  }
}

export async function confirmReferral(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/confirm-referral`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error("Failed to confirm referral");
  }
}
