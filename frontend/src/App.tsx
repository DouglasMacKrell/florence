import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import type { FormEvent } from "react";

import {
  confirmReferral,
  createSession,
  fetchDemoScript,
  getOperatorSession,
  getSession,
  intakeFieldLabel,
  leadCategoryLabel,
  selectProvider,
  sendMessageStream,
} from "./api";
import type { MatchResult, OperatorSession, SessionDetail, SessionMessage } from "./api";
import {
  enqueueSpeech,
  isSpeechSupported,
  prepareSpeechVoices,
  resetSpeechQueue,
  stopSpeech,
  waitForSpeechToFinish,
} from "./speech";
import { abortListening, isMicSupported, listenForSpeech, requestMicAccess } from "./mic";
import "./App.css";

const REQUIRED_INTAKE_FIELDS = [
  "caller.name",
  "caller.phone",
  "caller.relationship_to_care_recipient",
  "care_recipient.age",
  "location_preferences.postal_code",
  "care_needs",
  "timing.urgency",
  "financial.monthly_budget_max",
  "consent.consent_to_contact",
] as const;

const ALL_REQUIRED_FIELDS = [...REQUIRED_INTAKE_FIELDS];

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<SessionMessage[]>([]);
  const [matches, setMatches] = useState<MatchResult[]>([]);
  const [careRecommendation, setCareRecommendation] = useState<SessionDetail["care_recommendation"]>();
  const [completionPercent, setCompletionPercent] = useState(0);
  const [missingFields, setMissingFields] = useState<string[]>(ALL_REQUIRED_FIELDS);
  const [operatorView, setOperatorView] = useState<OperatorSession | null>(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [micEnabled, setMicEnabled] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [referralStatus, setReferralStatus] = useState<string | null>(null);
  const [demoRunning, setDemoRunning] = useState(false);
  const [liveUserTranscript, setLiveUserTranscript] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const micEnabledRef = useRef(false);

  const speechSupported = useMemo(() => isSpeechSupported(), []);
  const micSupported = useMemo(() => isMicSupported(), []);

  useEffect(() => {
    micEnabledRef.current = micEnabled;
  }, [micEnabled]);

  useEffect(() => {
    void bootstrapSession();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, matches, liveUserTranscript]);

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
    setMissingFields(
      detail.completion_percent === 0 && detail.missing_fields.length === 0
        ? ALL_REQUIRED_FIELDS
        : detail.missing_fields,
    );
    setReferralStatus(detail.referral?.status ?? null);
    if (detail.completion_percent > 0) {
      try {
        setOperatorView(await getOperatorSession(id));
      } catch {
        setOperatorView(null);
      }
    }
  }

  async function sendUserMessage(
    content: string,
    options?: { speakUserFirst?: boolean; speakAssistant?: boolean },
  ) {
    if (!sessionId) {
      return;
    }
    const shouldSpeakUser = options?.speakUserFirst === true;
    const shouldSpeakAssistant = options?.speakAssistant ?? voiceEnabled;
    setLiveUserTranscript(null);
    if (shouldSpeakUser) {
      await enqueueSpeech("user", content);
    }
    setMessages((current) => [...current, { role: "user", content }]);
    setMessages((current) => [...current, { role: "assistant", content: "" }]);
    const reply = await sendMessageStream(sessionId, content, (token) => {
      setMessages((current) => {
        const next = [...current];
        const last = next[next.length - 1];
        if (last?.role === "assistant") {
          next[next.length - 1] = { ...last, content: last.content + token };
        }
        return next;
      });
    });
    setMatches(reply.matches ?? []);
    setCareRecommendation(reply.care_recommendation);
    await refreshSession(sessionId);
    if (shouldSpeakAssistant) {
      abortListening();
      await enqueueSpeech("assistant", reply.content);
    }
    if (micEnabledRef.current && !demoRunning) {
      void scheduleMicListen(shouldSpeakAssistant ? 250 : 0);
    }
  }

  async function scheduleMicListen(delayMs = 0) {
    if (!micEnabledRef.current || demoRunning) {
      return;
    }
    window.setTimeout(() => {
      void maybeAutoListen();
    }, delayMs);
  }

  async function maybeAutoListen() {
    if (!micEnabledRef.current || !sessionId || loading || demoRunning || listening) {
      return;
    }
    setListening(true);
    setError(null);
    setLiveUserTranscript("");
    let sentMessage = false;
    try {
      await waitForSpeechToFinish();
      if (!micEnabledRef.current || demoRunning) {
        return;
      }
      const transcript = await listenForSpeech({
        onTranscript: (text) => {
          setLiveUserTranscript(text);
        },
      });
      if (!transcript.trim() || !micEnabledRef.current || demoRunning) {
        return;
      }
      sentMessage = true;
      setLoading(true);
      await sendUserMessage(transcript);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Microphone input failed");
    } finally {
      setListening(false);
      setLoading(false);
      if (!sentMessage) {
        setLiveUserTranscript(null);
      }
      if (!sentMessage && micEnabledRef.current && !demoRunning) {
        void scheduleMicListen(400);
      }
    }
  }

  async function handleEnableVoice() {
    if (!speechSupported) {
      setError("Speech is not supported in this browser");
      return;
    }
    setError(null);
    await prepareSpeechVoices();
    setVoiceEnabled(true);
    const latestAssistant = [...messages].reverse().find((message) => message.role === "assistant");
    if (latestAssistant?.content.trim()) {
      await enqueueSpeech("assistant", latestAssistant.content);
    }
  }

  function handleDisableVoice() {
    stopSpeech();
    resetSpeechQueue();
    setVoiceEnabled(false);
  }

  async function handleEnableMic() {
    if (!micSupported) {
      setError("Microphone input is not supported in this browser");
      return;
    }
    setError(null);
    const allowed = await requestMicAccess();
    if (!allowed) {
      setError("Microphone permission was denied");
      micEnabledRef.current = false;
      setMicEnabled(false);
      return;
    }
    micEnabledRef.current = true;
    setMicEnabled(true);
    await waitForSpeechToFinish();
    void scheduleMicListen(200);
  }

  function handleDisableMic() {
    micEnabledRef.current = false;
    setMicEnabled(false);
    setListening(false);
    setLiveUserTranscript(null);
    abortListening();
  }

  async function handleMicToggle() {
    if (micEnabledRef.current) {
      handleDisableMic();
      return;
    }
    await handleEnableMic();
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!sessionId || !input.trim() || loading || demoRunning) {
      return;
    }
    const content = input.trim();
    setInput("");
    setLoading(true);
    setError(null);
    try {
      await sendUserMessage(content);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to send message");
    } finally {
      setLoading(false);
    }
  }

  async function handleRunDemo() {
    if (loading || demoRunning) {
      return;
    }
    setDemoRunning(true);
    setLoading(true);
    setError(null);
    setMatches([]);
    setCareRecommendation(undefined);
    setReferralStatus(null);
    setOperatorView(null);
    setMissingFields(ALL_REQUIRED_FIELDS);
    setCompletionPercent(0);
    resetSpeechQueue();
    try {
      const useVoice = voiceEnabled || speechSupported;
      if (useVoice) {
        await prepareSpeechVoices();
        if (!voiceEnabled) {
          setVoiceEnabled(true);
        }
      }
      const script = await fetchDemoScript();
      const session = await createSession();
      setSessionId(session.session_id);
      setMessages([{ role: "assistant", content: session.greeting }]);
      if (useVoice) {
        await enqueueSpeech("assistant", session.greeting);
      }
      for (const message of script.user_messages) {
        await new Promise((resolve) => window.setTimeout(resolve, 400));
        await sendUserMessage(message, { speakUserFirst: useVoice, speakAssistant: useVoice });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Demo walkthrough failed");
    } finally {
      setLoading(false);
      setDemoRunning(false);
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

  async function startVoiceInput() {
    if (!micSupported) {
      setError("Microphone input is not supported in this browser");
      return;
    }
    setListening(true);
    setError(null);
    setLiveUserTranscript("");
    try {
      const transcript = await listenForSpeech({
        onTranscript: (text) => {
          setLiveUserTranscript(text);
        },
      });
      if (transcript) {
        setInput(transcript);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Microphone input failed");
    } finally {
      setListening(false);
      setLiveUserTranscript(null);
    }
  }

  function speak(text: string) {
    if (!speechSupported) {
      return;
    }
    void enqueueSpeech("assistant", text);
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <div className="site-header-main">
          <div className="brand-lockup">
            <div className="brand-mark" aria-hidden="true">
              F
            </div>
            <div className="brand-copy">
              <p className="brand-eyebrow">Arya Health · Care navigation</p>
              <h1 className="brand-title">Florence</h1>
              <p className="brand-lead">
                A compassionate guide for families exploring elder-care options — by text or voice.
              </p>
            </div>
          </div>

          <div className="header-panel">
            <div className="progress-meter">
              <div
                className="progress-ring"
                style={{ "--progress": `${completionPercent}%` } as CSSProperties}
                aria-hidden="true"
              >
                <span>{completionPercent}%</span>
              </div>
              <div className="progress-copy">
                <span className="progress-label">Intake progress</span>
                <strong>{completionPercent === 100 ? "Complete" : "In progress"}</strong>
              </div>
            </div>

            <div className="header-actions">
              {speechSupported ? (
                <button
                  type="button"
                  className={`header-pill${voiceEnabled ? " is-active" : ""}`}
                  title={voiceEnabled ? "Florence reads replies aloud" : "Enable Florence voice output"}
                  onClick={voiceEnabled ? handleDisableVoice : () => void handleEnableVoice()}
                  disabled={!voiceEnabled && (loading || demoRunning)}
                >
                  {voiceEnabled ? "Voice on" : "Voice"}
                </button>
              ) : null}
              {micSupported ? (
                <button
                  type="button"
                  className={`header-pill${micEnabled ? " is-active" : ""}`}
                  title={micEnabled ? "Turn off microphone input" : "Enable microphone input"}
                  aria-pressed={micEnabled}
                  onClick={() => void handleMicToggle()}
                  disabled={loading || demoRunning}
                >
                  {micEnabled ? "Mic on" : "Mic"}
                </button>
              ) : null}
              <button
                type="button"
                className="header-pill header-pill-primary"
                title="Replay the Queens daughter demo scenario"
                disabled={loading || demoRunning}
                onClick={() => void handleRunDemo()}
              >
                {demoRunning ? "Demo…" : "Run demo"}
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="layout">
        <section className="chat-panel">
          <div className="messages">
            {messages.map((message, index) => (
              <article key={`${message.role}-${index}`} className={`message ${message.role}`}>
                <span>{message.role === "assistant" ? "Florence" : "Caller"}</span>
                <p>{message.content}</p>
                {message.role === "assistant" && message.content && voiceEnabled ? (
                  <button type="button" className="ghost-button" onClick={() => speak(message.content)}>
                    Replay
                  </button>
                ) : null}
              </article>
            ))}
            {liveUserTranscript !== null ? (
              <article className="message user is-live">
                <span>Caller</span>
                <p>{liveUserTranscript || "Listening…"}</p>
              </article>
            ) : null}
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
              <button type="submit" disabled={loading || demoRunning || !input.trim()}>
                {loading ? "Sending..." : "Send"}
              </button>
              <button
                type="button"
                className="secondary"
                disabled={loading || demoRunning || !micSupported}
                onClick={() => void startVoiceInput()}
              >
                {listening ? "Listening…" : micEnabled ? "Speak now" : "Use mic"}
              </button>
            </div>
          </form>
          {error ? <p className="error">{error}</p> : null}
        </section>

        <aside className="side-panel">
          <section className="info-card intake-card">
            <h2>Intake checklist</h2>
            <ul className="intake-checklist">
              {REQUIRED_INTAKE_FIELDS.map((field) => {
                const complete =
                  completionPercent > 0 ? !missingFields.includes(field) : false;
                return (
                  <li key={field} className={complete ? "complete" : "pending"}>
                    <span>{complete ? "✓" : "○"}</span>
                    {intakeFieldLabel(field)}
                  </li>
                );
              })}
            </ul>
          </section>

          {operatorView ? (
            <section className="info-card operator-card">
              <h2>Operator view</h2>
              <p className="operator-score">
                Lead score <strong>{operatorView.lead_score}</strong>
                <span className="pill">{leadCategoryLabel(operatorView.lead_category)}</span>
              </p>
              {operatorView.referral?.estimated_referral_value ? (
                <p className="referral-value">
                  Est. referral value: $
                  {operatorView.referral.estimated_referral_value.toLocaleString()}
                </p>
              ) : null}
              {operatorView.matches.length > 0 ? (
                <div className="operator-matches">
                  <h3>Internal match economics</h3>
                  <ul>
                    {operatorView.matches.map((match) => (
                      <li key={match.provider_id}>
                        {match.provider_id}: ${match.estimated_referral_value?.toLocaleString() ?? "0"}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </section>
          ) : null}

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
