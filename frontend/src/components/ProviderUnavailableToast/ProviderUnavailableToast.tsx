/**
 * ProviderUnavailableToast — Phase 15.5
 *
 * Shows a dismissable amber banner when the backend returns HTTP 503
 * with error:"all_providers_unavailable", meaning every LLM tier
 * (Ultra → Lightning → Haiku) has failed simultaneously.
 *
 * Subscribes to React Query's mutation and query caches so any hook
 * anywhere in the tree can trigger it — no prop-drilling needed.
 */

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ApiError } from "../../api/client";

const TOAST_CODE = "all_providers_unavailable";

export function ProviderUnavailableToast() {
  const queryClient = useQueryClient();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Subscribe to query cache errors (GET requests)
    const qCache = queryClient.getQueryCache();
    const unsubQ = qCache.subscribe((event) => {
      if (
        event.type === "updated" &&
        event.query.state.status === "error"
      ) {
        const err = event.query.state.error;
        if (err instanceof ApiError && err.code === TOAST_CODE) {
          setVisible(true);
        }
      }
    });

    // Subscribe to mutation cache errors (POST/PATCH/DELETE requests)
    const mCache = queryClient.getMutationCache();
    const unsubM = mCache.subscribe((event) => {
      if (
        event.type === "updated" &&
        event.mutation?.state.status === "error"
      ) {
        const err = event.mutation.state.error;
        if (err instanceof ApiError && err.code === TOAST_CODE) {
          setVisible(true);
        }
      }
    });

    return () => {
      unsubQ();
      unsubM();
    };
  }, [queryClient]);

  if (!visible) return null;

  return (
    <div
      role="alert"
      style={{
        position: "fixed",
        bottom: "1.25rem",
        left: "50%",
        transform: "translateX(-50%)",
        zIndex: 9999,
        display: "flex",
        alignItems: "flex-start",
        gap: "0.75rem",
        padding: "0.875rem 1.125rem",
        borderRadius: "8px",
        background: "#fefce8",
        border: "1px solid #fbbf24",
        boxShadow: "0 4px 16px rgba(0,0,0,0.12)",
        maxWidth: "min(520px, calc(100vw - 2rem))",
        width: "max-content",
      }}
    >
      <span style={{ fontSize: "1.25rem", lineHeight: 1, flexShrink: 0 }}>⚠️</span>
      <div style={{ flex: 1 }}>
        <p style={{ margin: 0, fontWeight: 600, fontSize: "0.9rem", color: "#92400e" }}>
          AI providers temporarily unavailable
        </p>
        <p style={{ margin: "0.2rem 0 0", fontSize: "0.8125rem", color: "#78350f" }}>
          All language model tiers are down right now. Your action was not completed.
          Please wait ~2 minutes and try again.
        </p>
      </div>
      <button
        aria-label="Dismiss"
        onClick={() => setVisible(false)}
        style={{
          flexShrink: 0,
          background: "none",
          border: "none",
          cursor: "pointer",
          fontSize: "1.1rem",
          color: "#92400e",
          lineHeight: 1,
          padding: "0.125rem",
        }}
      >
        ✕
      </button>
    </div>
  );
}
