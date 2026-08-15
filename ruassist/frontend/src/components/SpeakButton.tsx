import { useEffect, useState } from "react";
import { canSpeak, onVoicesReady, speak } from "../speech";

/**
 * Rendered only when the platform actually has a Russian voice installed.
 * A button that does nothing when pressed is worse than no button.
 */
export function SpeakButton({ text, label }: { text: string; label?: string }) {
  const [available, setAvailable] = useState(canSpeak);

  useEffect(() => onVoicesReady(() => setAvailable(canSpeak())), []);

  if (!available) return null;
  return (
    <button
      type="button"
      className="speak"
      onClick={() => speak(text)}
      aria-label={label ?? `朗读 ${text}`}
      title="朗读"
    >
      🔊
    </button>
  );
}
