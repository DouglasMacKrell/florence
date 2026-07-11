interface SpeechRecognitionAlternativeLike {
  transcript: string;
}

interface SpeechRecognitionResultLike {
  readonly [index: number]: SpeechRecognitionAlternativeLike;
  isFinal: boolean;
}

interface SpeechRecognitionResultsLike {
  readonly length: number;
  readonly [index: number]: SpeechRecognitionResultLike;
}

interface SpeechRecognitionEventLike {
  results: SpeechRecognitionResultsLike;
  resultIndex: number;
}

interface SpeechRecognitionInstance {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onstart: (() => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionInstance;

declare global {
  interface Window {
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
    SpeechRecognition?: SpeechRecognitionConstructor;
  }
}

export type SpeechListenOptions = {
  onTranscript?: (text: string, isFinal: boolean) => void;
};

export function isMicSupported(): boolean {
  return Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
}

function createRecognition(): SpeechRecognitionInstance | null {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  return Recognition ? new Recognition() : null;
}

let activeRecognition: SpeechRecognitionInstance | null = null;

export function abortListening(): void {
  if (!activeRecognition) {
    return;
  }
  try {
    activeRecognition.abort();
  } catch {
    // Ignore browsers that reject abort while idle.
  }
  activeRecognition = null;
}

export async function requestMicAccess(): Promise<boolean> {
  if (navigator.mediaDevices?.getUserMedia) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      for (const track of stream.getTracks()) {
        track.stop();
      }
      return true;
    } catch {
      return false;
    }
  }

  const recognition = createRecognition();
  if (!recognition) {
    return false;
  }

  return new Promise((resolve) => {
    let settled = false;
    const finish = (allowed: boolean) => {
      if (settled) {
        return;
      }
      settled = true;
      resolve(allowed);
    };

    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.onresult = () => finish(true);
    recognition.onend = () => finish(true);
    recognition.onerror = () => finish(false);

    try {
      recognition.start();
    } catch {
      finish(false);
    }

    window.setTimeout(() => finish(true), 2500);
  });
}

export function listenForSpeech(options?: SpeechListenOptions): Promise<string> {
  const recognition = createRecognition();
  if (!recognition) {
    return Promise.reject(new Error("Microphone input is not supported in this browser"));
  }

  abortListening();
  activeRecognition = recognition;

  return new Promise((resolve, reject) => {
    let settled = false;
    let latestTranscript = "";

    const finish = (handler: () => void) => {
      if (settled) {
        return;
      }
      settled = true;
      if (activeRecognition === recognition) {
        activeRecognition = null;
      }
      handler();
    };

    recognition.lang = "en-US";
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.onresult = (event: SpeechRecognitionEventLike) => {
      let interim = "";
      let final = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        const part = result?.[0]?.transcript ?? "";
        if (result?.isFinal) {
          final += part;
        } else {
          interim += part;
        }
      }
      latestTranscript = `${final}${interim}`.trim();
      options?.onTranscript?.(latestTranscript, final.trim().length > 0);
    };
    recognition.onerror = () => {
      finish(() => reject(new Error("Microphone input failed")));
    };
    recognition.onend = () => {
      finish(() => resolve(latestTranscript.trim()));
    };

    try {
      recognition.start();
    } catch {
      finish(() => reject(new Error("Unable to start microphone input")));
    }
  });
}
