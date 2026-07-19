import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "tbs-ble-tutorial-progress-v1";

function readStore(): Record<string, boolean> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    return parsed && typeof parsed === "object" ? (parsed as Record<string, boolean>) : {};
  } catch {
    return {};
  }
}

export function useChapterProgress() {
  const [done, setDone] = useState<Record<string, boolean>>(() =>
    typeof window !== "undefined" ? readStore() : {},
  );

  useEffect(() => {
    setDone(readStore());
  }, []);

  const isComplete = useCallback((labId: string) => Boolean(done[labId]), [done]);

  const markComplete = useCallback((labId: string) => {
    setDone((prev) => {
      if (prev[labId]) return prev;
      const next = { ...prev, [labId]: true };
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        /* ignore quota */
      }
      return next;
    });
  }, []);

  const clearProgress = useCallback(() => {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
    setDone({});
  }, []);

  return { isComplete, markComplete, clearProgress, done };
}
