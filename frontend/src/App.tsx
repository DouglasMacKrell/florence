import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import {
  confirmReferral,
  createSession,
  getSession,
  MatchResult,
  selectProvider,
  sendMessage,
  SessionDetail,
  SessionMessage,
} from "./api";
import "./App.css";

type SpeechRecognitionConstructor = new () => SpeechRecognition;

declare global {
  interface Window {
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
    SpeechRecognition?: SpeechRecognitionConstructor;
  }
}

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<SessionMessage[]>([]);
  const [matches, setMatches] = useState<MatchResult[]>([]);
  const [careRecommendation, setCareRecommendation] = useState<SessionDetail["care_recommendation"]>();
  const [completionPercent, setCompletionPercent] = useState(0);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [referralStatus, setReferralStatus] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const speechSupported = useMemo(
    () => Boolean(window.SpeechRecognition || window.webkitSpeechRecognition),
    [],
  );

  useEffect(() => {
    void bootstrapSession();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, matches]);

  async function bootstrapSession() {
    setLoading(true);
    setError(null);
    try {
      const session = await createSession();
      setSessionId(session.session_id);
      setMessages([{ role: "assistant", content: session.greeting }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to start session");
    } finally {
      setLoading(false);
    }
  }

  async function refreshSession(id: string) {
    const detail = await getSession(id);
    setMessages(detail.messages);
    setMatches(detail.matches);
    setCareRecommendation(detail.care_recommendation);
    setCompletionPercent(detail.completion_percent);
    setReferralStatus(detail.referral?.status ?? null);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!sessionId || !input.trim() || loading) {
      return;
    }
    const content = input.trim();
    setInput("");
    setMessages((current) => [...current, { role: "user", content }]);
    setLoading(true);
    setError(null);
    try {
      const reply = await sendMessage(sessionId, content);
      setMessages((current) => [...current, { role: "assistant", content: reply.content }]);
      setMatches(reply.matches ?? []);
      setCareRecommendation(reply.care_recommendation);
      await refreshSession(sessionId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to send message");
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectProvider(providerId: string) {
    if (!sessionId) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await selectProvider(sessionId, providerId);
      await confirmReferral(sessionId);
      await refreshSession(sessionId);
      setReferralStatus("mock_complete");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to submit referral");
    } finally {
      setLoading(false);
    }
  }

  function startVoiceInput() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {
      setError("Browser speech recognition is not available");
      return;
    }
    const recognition = new Recognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.onstart = () => setListening(true);
    recognition.onend = () => setListening(false);
    recognition.onerror = () => {
      setListening(false);
      setError("Voice input failed");
    };
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript;
      if (transcript) {
        setInput(transcript);
      }
    };
    recognition.start();
  }

  function speak(text: string) {
    if (!("speechSynthesis" in window)) {
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    window.speechSynthesis.speak(utterance);
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Florence · Arya Health Hackathon</p>
          <h1>Elder-care navigation</h1>
          <p className="subtitle">
            Text or voice intake, care-type guidance, provider matches, and mock referral submission.
          </p>
        </div>
        <div className="progress-card">
          <span>Intake progress</span>
          <strong>{completionPercent}%</strong>
        </div>
      </header>

      <main className="layout">
        <section className="chat-panel">
          <div className="messages">
            {messages.map((message, index) => (
              <article key={`${message.role}-${index}`} className={`message ${message.role}`}>
                <span>{message.role === "assistant" ? "Florence" : "You"}</span>
                <p>{message.content}</p>
                {message.role === "assistant" ? (
                  <button type="button" className="ghost-button" onClick={() => speak(message.content)}>
                    Listen
                  </button>
                ) : null}
              </article>
            ))}
            <div ref={messagesEndRef} />
          </div>

          <form className="composer" onSubmit={handleSubmit}>
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Describe the care situation or answer Florence's question..."
              rows={3}
            />
            <div className="composer-actions">
              <button type="submit" disabled={loading || !input.trim()}>
                {loading ? "Sending..." : "Send"}
              </button>
              <button
                type="button"
                className="secondary"
                disabled={loading || !speechSupported}
                onClick={startVoiceInput}
              >
                {listening ? "Listening..." : "Voice input"}
              </button>
            </div>
          </form>
          {error ? <p className="error">{error}</p> : null}
        </section>

        <aside className="side-panel">
          {careRecommendation ? (
            <section className="info-card">
              <h2>Care recommendation</h2>
              <p className="pill">{careRecommendation.primary.replaceAll("_", " ")}</p>
              <p>{careRecommendation.rationale}</p>
            </section>
          ) : null}

          {matches.length > 0 ? (
            <section className="info-card">
              <h2>Provider matches</h2>
              <div className="provider-list">
                {matches.map((match) => (
                  <article key={match.provider_id} className="provider-card">
                    <div className="provider-card-header">
                      <strong>{match.provider_id}</strong>
                      <span>Score {match.score}</span>
                    </div>
                    <ul>
                      {match.strengths.slice(0, 3).map((strength) => (
                        <li key={strength}>{strength}</li>
                      ))}
                    </ul>
                    <button type="button" onClick={() => void handleSelectProvider(match.provider_id)}>
                      Select provider
                    </button>
                  </article>
                ))}
              </div>
            </section>
          ) : null}

          {referralStatus ? (
            <section className="info-card success">
              <h2>Referral status</h2>
              <p>{referralStatus}</p>
            </section>
          ) : null}
        </aside>
      </main>
    </div>
  );
}

export default App;
