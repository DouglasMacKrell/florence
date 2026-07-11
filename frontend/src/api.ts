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
