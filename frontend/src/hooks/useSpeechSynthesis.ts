/**
 * useSpeechSynthesis — Phase 18.6
 * Wraps the Web Speech API speechSynthesis for Read Aloud in LessonModal.
 */

import { useCallback, useEffect, useRef, useState } from "react";

export interface UseSpeechSynthesisReturn {
  speak: (text: string, rate?: number) => void;
  stop: () => void;
  isPlaying: boolean;
}

export function useSpeechSynthesis(): UseSpeechSynthesisReturn {
  const [isPlaying, setIsPlaying] = useState(false);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  const stop = useCallback(() => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    setIsPlaying(false);
    utteranceRef.current = null;
  }, []);

  const speak = useCallback(
    (text: string, rate = 1) => {
      if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
      window.speechSynthesis.cancel();

      const utter = new SpeechSynthesisUtterance(text);
      utter.rate = rate;
      utter.onstart = () => setIsPlaying(true);
      utter.onend = () => { setIsPlaying(false); utteranceRef.current = null; };
      utter.onerror = () => { setIsPlaying(false); utteranceRef.current = null; };

      utteranceRef.current = utter;
      window.speechSynthesis.speak(utter);
    },
    []
  );

  useEffect(() => {
    return () => {
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  return { speak, stop, isPlaying };
}
