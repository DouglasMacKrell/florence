export type SpeechRole = "assistant" | "user";

const FEMALE_VOICE_HINTS = ["Samantha", "Karen", "Moira", "Victoria", "Female", "Zira", "Allison"];
const MALE_VOICE_HINTS = ["Daniel", "Alex", "Fred", "Male", "David", "Tom", "Aaron", "Gordon"];

let assistantVoiceName: string | null = null;
let userVoiceName: string | null = null;
let speechChain: Promise<void> = Promise.resolve();

function englishVoices(): SpeechSynthesisVoice[] {
  return window.speechSynthesis.getVoices().filter((voice) => voice.lang.startsWith("en"));
}

function pickVoice(candidates: SpeechSynthesisVoice[], hints: string[]): SpeechSynthesisVoice | null {
  for (const hint of hints) {
    const match = candidates.find((voice) => voice.name.includes(hint));
    if (match) {
      return match;
    }
  }
  return null;
}

function assignVoices(): void {
  const voices = englishVoices();
  if (voices.length === 0) {
    return;
  }

  const assistant = pickVoice(voices, FEMALE_VOICE_HINTS) ?? voices[0];
  const remaining = voices.filter(
    (voice) => voice.voiceURI !== assistant.voiceURI && voice.name !== assistant.name,
  );
  const user =
    pickVoice(remaining, MALE_VOICE_HINTS) ??
    remaining.find((voice) => !voice.name.includes("Female")) ??
    remaining[0] ??
    null;

  assistantVoiceName = assistant.name;
  userVoiceName = user?.name ?? null;
}

function resolveVoice(role: SpeechRole): SpeechSynthesisVoice | null {
  if (!assistantVoiceName) {
    assignVoices();
  }

  const voices = englishVoices();
  const targetName = role === "assistant" ? assistantVoiceName : userVoiceName;
  if (!targetName) {
    return null;
  }

  const match = voices.find((voice) => voice.name === targetName);
  if (match) {
    return match;
  }

  assignVoices();
  const refreshedName = role === "assistant" ? assistantVoiceName : userVoiceName;
  return voices.find((voice) => voice.name === refreshedName) ?? null;
}

function waitForSpeechIdle(): Promise<void> {
  return new Promise((resolve) => {
    const check = () => {
      if (!window.speechSynthesis.speaking && !window.speechSynthesis.pending) {
        resolve();
        return;
      }
      window.setTimeout(check, 40);
    };
    check();
  });
}

export function isSpeechSupported(): boolean {
  return "speechSynthesis" in window;
}

export function prepareSpeechVoices(): Promise<void> {
  if (!isSpeechSupported()) {
    return Promise.resolve();
  }

  return new Promise((resolve) => {
    const finish = () => {
      assignVoices();
      resolve();
    };

    assignVoices();
    if (assistantVoiceName && userVoiceName) {
      resolve();
      return;
    }

    window.speechSynthesis.onvoiceschanged = () => {
      window.speechSynthesis.onvoiceschanged = null;
      finish();
    };
    window.speechSynthesis.getVoices();
    window.setTimeout(finish, 400);
  });
}

function speakOnce(role: SpeechRole, text: string): Promise<void> {
  if (!isSpeechSupported() || !text.trim()) {
    return Promise.resolve();
  }

  return waitForSpeechIdle().then(
    () =>
      new Promise((resolve) => {
        const utterance = new SpeechSynthesisUtterance(text);
        const voice = resolveVoice(role);
        const assistantVoice = resolveVoice("assistant");
        const activeVoice = voice ?? (role === "user" ? assistantVoice : null);

        if (activeVoice) {
          utterance.voice = activeVoice;
        }

        utterance.rate = role === "assistant" ? 0.95 : 1.02;

        if (role === "user") {
          const sameVoice =
            activeVoice &&
            assistantVoice &&
            (activeVoice.voiceURI === assistantVoice.voiceURI ||
              activeVoice.name === assistantVoice.name);
          utterance.pitch = sameVoice ? 0.65 : 0.88;
        } else {
          utterance.pitch = 1;
        }

        utterance.onend = () => resolve();
        utterance.onerror = () => resolve();
        window.speechSynthesis.speak(utterance);
      }),
  );
}

export function enqueueSpeech(role: SpeechRole, text: string): Promise<void> {
  speechChain = speechChain.then(() => speakOnce(role, text));
  return speechChain;
}

export function stopSpeech(): void {
  if (isSpeechSupported()) {
    window.speechSynthesis.cancel();
  }
  speechChain = Promise.resolve();
}

export function resetSpeechQueue(): void {
  stopSpeech();
}

export async function waitForSpeechToFinish(): Promise<void> {
  await speechChain.catch(() => undefined);
  await waitForSpeechIdle();
}

export function getAssignedVoiceNames(): { assistant: string | null; user: string | null } {
  return { assistant: assistantVoiceName, user: userVoiceName };
}
