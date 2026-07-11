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
  estimated_referral_value?: number | null;
};

export type SessionDetail = {
  session_id: string;
  state: string;
  status: string;
  intake: IntakeRecord;
  completion_percent: number;
  missing_fields: string[];
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

export type OperatorSession = {
  session_id: string;
  state: string;
  status: string;
  completion_percent: number;
  missing_fields: string[];
  lead_score: number;
  lead_category: string;
  lead_breakdown: Record<string, number>;
  transcript: SessionMessage[];
  matches: MatchResult[];
  care_recommendation?: SessionDetail["care_recommendation"];
  referral?: {
    provider_id: string;
    status: string;
    estimated_referral_value?: number | null;
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

type StreamMessageResult = {
  content: string;
  state: string;
  intake: IntakeRecord;
  matches?: MatchResult[];
  care_recommendation?: SessionDetail["care_recommendation"];
};

function parseSseBlock(block: string): { event: string; data: Record<string, unknown> } | null {
  if (!block.trim()) {
    return null;
  }
  let event = "message";
  let dataText = "";
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataText = line.slice(5).trim();
    }
  }
  if (!dataText) {
    return null;
  }
  return { event, data: JSON.parse(dataText) as Record<string, unknown> };
}

export async function sendMessageStream(
  sessionId: string,
  content: string,
  onToken: (text: string) => void,
): Promise<StreamMessageResult> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/messages/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("Session expired — refresh the page to start a new conversation");
    }
    throw new Error("Failed to send message");
  }
  if (!response.body) {
    throw new Error("Streaming is not supported in this browser");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: StreamMessageResult | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";
    for (const block of blocks) {
      const parsed = parseSseBlock(block);
      if (!parsed) {
        continue;
      }
      if (parsed.event === "token" && typeof parsed.data.text === "string") {
        onToken(parsed.data.text);
      } else if (parsed.event === "error") {
        throw new Error(String(parsed.data.detail ?? "Streaming failed"));
      } else if (parsed.event === "done") {
        result = {
          content: String(parsed.data.content ?? ""),
          state: String(parsed.data.state ?? ""),
          intake: parsed.data.intake as IntakeRecord,
          matches: parsed.data.matches as MatchResult[] | undefined,
          care_recommendation: parsed.data.care_recommendation as
            | SessionDetail["care_recommendation"]
            | undefined,
        };
      }
    }
  }

  if (!result) {
    throw new Error("Stream ended without a final response");
  }
  return result;
}

export async function getSession(sessionId: string): Promise<SessionDetail> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}`);
  if (!response.ok) {
    throw new Error("Failed to load session");
  }
  return response.json();
}

export async function getOperatorSession(sessionId: string): Promise<OperatorSession> {
  const response = await fetch(`${API_BASE}/operator/sessions/${sessionId}`);
  if (!response.ok) {
    throw new Error("Failed to load operator view");
  }
  return response.json();
}

const INTAKE_FIELD_LABELS: Record<string, string> = {
  "caller.name": "Caller name",
  "caller.phone": "Contact phone",
  "caller.relationship_to_care_recipient": "Relationship to care recipient",
  "care_recipient.age": "Care recipient age",
  "location_preferences.postal_code": "Location / ZIP code",
  "care_needs": "Care needs",
  "timing.urgency": "Timing / urgency",
  "financial.monthly_budget_max": "Budget",
  "consent.consent_to_contact": "Consent to follow up",
};

export function intakeFieldLabel(field: string): string {
  return INTAKE_FIELD_LABELS[field] ?? field;
}

export function leadCategoryLabel(category: string): string {
  return category.replaceAll("_", " ");
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

export type DemoScript = {
  id: string;
  title: string;
  description: string;
  user_messages: string[];
};

export async function fetchDemoScript(): Promise<DemoScript> {
  const response = await fetch(`${API_BASE}/demo/script`);
  if (!response.ok) {
    throw new Error("Failed to load demo script");
  }
  return response.json();
}
