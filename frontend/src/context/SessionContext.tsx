/**
 * SessionContext — Step 5.2
 *
 * Populated from GET /auth/me on app load.
 * Holds identity for the entire app lifetime.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import type { MeResponse } from "../api/types";
import { auth } from "../api";

interface SessionState {
  /** null = not yet loaded; undefined = loaded but no session */
  session: MeResponse | null | undefined;
  isLoading: boolean;
  /** Call after login to refresh session state without a full page reload */
  refresh: () => Promise<void>;
  /** Call after logout to clear state */
  clear: () => void;
}

const SessionContext = createContext<SessionState>({
  session: null,
  isLoading: true,
  refresh: async () => {},
  clear: () => {},
});

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<MeResponse | null | undefined>(null);
  const [isLoading, setIsLoading] = useState(true);

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      const me = await auth.me();
      setSession(me);
    } catch {
      // 401 = no session
      setSession(undefined);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const clear = useCallback(() => {
    setSession(undefined);
  }, []);

  return (
    <SessionContext.Provider value={{ session, isLoading, refresh: load, clear }}>
      {children}
    </SessionContext.Provider>
  );
}

/** Hook to read the current session from anywhere in the tree. */
export function useSession(): SessionState {
  return useContext(SessionContext);
}

/** Convenience: returns true while the initial /auth/me is in-flight. */
export function useSessionLoading(): boolean {
  return useContext(SessionContext).isLoading;
}
