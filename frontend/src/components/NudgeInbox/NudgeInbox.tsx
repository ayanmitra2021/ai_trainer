/**
 * NudgeInbox — shows a practitioner's received nudges with read/unread state.
 * Used inside TrendDashboard tab.
 */
import { useMarkNudgeRead, usePractitionerNudges } from "../../hooks";
import type { NudgeExtended } from "../../api/types";

interface Props {
  practitionerId: string;
}

function NudgeCard({ nudge }: { nudge: NudgeExtended }) {
  const markRead = useMarkNudgeRead();
  const isUnread = !nudge.is_read;

  return (
    <div
      className="card"
      style={{
        cursor: isUnread ? "pointer" : "default",
        borderLeft: isUnread ? "3px solid var(--primary)" : "3px solid transparent",
        marginBottom: "0.625rem",
      }}
      onClick={() => {
        if (isUnread) markRead.mutate(nudge.id);
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", gap: "0.75rem" }}>
        {isUnread && (
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "var(--primary)",
              flexShrink: 0,
              marginTop: "0.35rem",
            }}
          />
        )}
        <div style={{ flex: 1 }}>
          {nudge.subject && (
            <div style={{ fontWeight: isUnread ? 600 : 400, marginBottom: "0.25rem" }}>
              {nudge.subject}
            </div>
          )}
          <p style={{ margin: 0, fontSize: "0.875rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
            {nudge.content}
          </p>
          <p style={{ margin: "0.375rem 0 0", fontSize: "0.75rem", color: "var(--text-muted)" }}>
            {new Date(nudge.created_at).toLocaleDateString()}
            {nudge.is_read && nudge.read_at
              ? ` · Read ${new Date(nudge.read_at).toLocaleDateString()}`
              : ""}
          </p>
        </div>
      </div>
    </div>
  );
}

export default function NudgeInbox({ practitionerId }: Props) {
  const { data: nudges, isLoading } = usePractitionerNudges(practitionerId);

  if (isLoading) {
    return (
      <div style={{ textAlign: "center", padding: "2rem" }}>
        <span className="spinner" />
      </div>
    );
  }

  return (
    <div style={{ marginTop: "2rem" }}>
      <h3 style={{ marginBottom: "0.75rem" }}>Messages</h3>
      {(!nudges || nudges.length === 0) ? (
        <div className="empty-state" style={{ fontSize: "0.875rem" }}>
          No messages yet. Messages from your learning team will appear here.
        </div>
      ) : (
        nudges.map((n) => <NudgeCard key={n.id} nudge={n} />)
      )}
    </div>
  );
}
