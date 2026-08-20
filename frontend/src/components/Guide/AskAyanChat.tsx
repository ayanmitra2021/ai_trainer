import { useState, useRef, useEffect, useCallback } from "react";

// ---------------------------------------------------------------------------
// Static keyword-match response engine — zero API calls, zero LLM
// ---------------------------------------------------------------------------

interface Topic {
  keywords: string[];
  answer: string;
}

const TOPICS: Topic[] = [
  {
    keywords: ["skill radar", "radar", "mastery score", "mastery", "spider", "polygon"],
    answer:
      "The **Skill Radar** is your learning command centre. It's a polygon chart where each spoke represents a skill from your chosen certification's blueprint. The further out the dot, the higher your mastery. Mastery scores move *only* from quiz answers — the radar is evidence-based, not self-reported. The **Domain Gap Chart** below it tracks exam-domain readiness separately, driven only by *Exam Relevant* quiz questions.",
  },
  {
    keywords: ["quiz", "question", "generating", "pending", "baking", "failed", "retry", "item", "trap", "reveal"],
    answer:
      "Questions are generated **per-skill in the background** right after your learning path is created. Each skill tab shows one of three states: ⏳ Pending (still baking), ✅ Ready (dive in!), or ⚠️ Failed (hit the '↻ Retry Failed Skills' button). The **trap-reveal mechanic** is the secret sauce — each wrong answer reveals *why* you went wrong, not just the right answer. Questions tagged '📋 Exam Relevant' move your domain score; '💡 Good to Know' questions build understanding but don't affect exam readiness.",
  },
  {
    keywords: ["byte", "lesson", "micro", "read aloud", "tts", "speech", "timer", "read again"],
    answer:
      "**Byte-Sized Learning** shows up in your Skill Radar tab, above the Learning Journey. Each row is a targeted micro-article written for a specific skill gap. Click **Read** to open the modal — a circular timer tracks your reading time. Hit 🔊 **Read Aloud** to have the lesson read at your chosen speed (0.75× to 2×). If you close the modal too quickly, you'll see *⚡ Read again* — the system noticed you didn't spend enough time. Lessons are regenerated fresh each time you regenerate your path.",
  },
  {
    keywords: ["mock exam", "mock", "exam", "abandon", "confidence", "pause", "resume", "confidence score", "exam ready"],
    answer:
      "You can take a **Mock Exam** any time from the Skill Radar tab — no mastery gate. The exam simulates the real certification format: timed, domain-weighted, with instant per-question feedback. You can **pause** and come back later, or **abandon** it (with a reason). Abandoned sessions aren't wasted — their unanswered questions get *recycled* into your next exam at no extra AI cost! The **Exam Confidence Score** on your Adoption Trends tab shows a recency-weighted average of all completed exams vs. the passing threshold. 🏅 *Exam Ready* appears when you're consistently above the bar.",
  },
  {
    keywords: ["nudge", "inbox", "adoption", "trend", "adoption trends", "message", "unread"],
    answer:
      "The **Adoption Trends** tab shows two things: (1) your skill mastery trend over time, and (2) your **Nudge Inbox**. Nudges are personalised messages your admin sends when they spot a gap between what you've learned and what shows up in your actual work. They arrive as cards in your inbox — unread ones show a count on the tab label. Click a nudge to mark it read.",
  },
  {
    keywords: ["profile", "certification", "cert", "domain", "assessment", "lock", "build profile", "self-assessment"],
    answer:
      "Your **Profile** is the foundation of everything. It starts with picking a certification — Anthropic, AWS, Google Cloud, Microsoft, or others. Then you rate yourself on the cert's key skills (this gives the system a starting baseline). Once you submit, your profile **locks** and the Domain Scorer maps your self-ratings to the cert's official exam domains. From that point, *quiz answers are the only thing that changes your scores*. You can have multiple profiles for different certs — switch between them from 'My Profiles' in the nav.",
  },
  {
    keywords: ["path", "learning path", "curriculum", "regenerate", "generate path", "journey"],
    answer:
      "Your **Learning Path** is the ordered list of skills the system thinks you should focus on, weighted toward your chosen certification's exam domains. It's generated automatically when you lock your profile and regenerated any time you click *Regenerate Path*. Each generation also kicks off background tasks that write fresh quiz questions and byte-sized lessons for your current skill gaps.",
  },
  {
    keywords: ["admin", "observability", "agent run", "campaign", "nudge campaign", "cert domain", "practitioner list"],
    answer:
      "Admins have extra tools: **Observability** shows every LLM agent call (model used, latency, token count, status) — great for diagnosing stuck quizzes. **Cert Domains** lets you trigger the AI-powered domain-refresh agent and approve or reject its proposals. **Nudges** is the campaign tool — generate categories, preview who qualifies, compose a message, and send it. The LLM in the Nudge flow *never* sees individual practitioner names or scores — only aggregated counts. Admins can also view the **Activity tab** on any practitioner's profile, and **deactivate accounts** if needed.",
  },
  {
    keywords: ["activity", "activity tab", "quiz history", "quiz rounds", "deactivate", "reactivate", "deactivation", "block login", "is_active", "account blocked"],
    answer:
      "The **Activity tab** in the admin practitioner view shows all engagement signals in one screen: 4 summary cards (Quiz Rounds, Correct Rate, Lesson Time, Mock Exams), a **per-skill table** (mastery %, gap %, quiz rounds, correct/wrong counts, lesson time), and a **Mock Exam History table**. Everything is read-only. To **deactivate** a practitioner (block their login), click the *Deactivate Account* button at the top of their admin profile view. Their data is fully preserved; you can *Reactivate* at any time. Only full admins (not leadership-role) can deactivate accounts.",
  },
  {
    keywords: ["login", "log in", "password", "account", "session", "email"],
    answer:
      "Practitioners log in with just their **email + name** — no password needed. If you've logged in before, the system recognises your email and restores your existing profile, quiz history, and progress automatically. Admins log in with an email + password (first-time password is *welcome*, and you'll be forced to change it on first login). Sessions are server-side cookies — nothing is stored in your browser.",
  },
];

const OFF_TOPIC_RESPONSES = [
  "That's a fascinating question… but I only know about Mastery Pulse! Try asking me about your Skill Radar, quizzes, or mock exams 😄",
  "Hmm, I'm just a portal guide embedded in a TypeScript file — philosophy isn't really my forte. Ask me about certification domains instead! 🤔",
  "Even Ayan wouldn't know the answer to that one. But I *do* know how byte-sized lessons work. Want to hear? 🎓",
  "I checked my entire knowledge base (it's one `.tsx` file) and found nothing about that. But ask me about quiz generation — I'm very proud of that answer 📚",
  "My training data is exclusively Mastery Pulse documentation. For everything else, there's Google 🔍",
  "Bold question! Unfortunately my expertise stops at the edges of this portal. Ask me something about mock exams — I'll knock it out of the park 🎯",
  "I'm sure that's important in the wider world. In *this* world (the Mastery Pulse portal), I'm your guide. What can I help you with here? 🌐",
  "That topic is outside my jurisdiction. My jurisdiction is roughly 'everything on this page' and not much else 😂",
];

function respondToQuestion(input: string): string {
  const text = input.toLowerCase().trim();
  if (!text) return "Go ahead — ask me anything about the portal!";

  for (const topic of TOPICS) {
    if (topic.keywords.some((kw) => text.includes(kw))) {
      return topic.answer;
    }
  }

  // Off-topic — pick a random funny response
  return OFF_TOPIC_RESPONSES[Math.floor(Math.random() * OFF_TOPIC_RESPONSES.length)];
}

// ---------------------------------------------------------------------------
// Markdown-like renderer: bold (**text**) and italic (*text*)
// ---------------------------------------------------------------------------
function renderAnswer(text: string) {
  // Split on bold or italic markers
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("*") && part.endsWith("*")) {
      return <em key={i}>{part.slice(1, -1)}</em>;
    }
    return <span key={i}>{part}</span>;
  });
}

// ---------------------------------------------------------------------------
// Suggestion chips shown below the welcome message
// ---------------------------------------------------------------------------
const SUGGESTIONS = [
  "How does the Skill Radar work?",
  "Tell me about mock exams",
  "What is byte-sized learning?",
  "How do quizzes work?",
  "What is the Activity tab?",
];

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface Message {
  role: "user" | "ayan" | "typing";
  text: string;
}

const WELCOME: Message = {
  role: "ayan",
  text: "Hi! I'm Ayan's guide assistant 👋 Ask me anything about the Mastery Pulse portal — quizzes, skill radar, mock exams, byte-sized lessons, or admin features. Or pick a question below to get started.",
};

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export function AskAyanChat() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to newest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // Focus input when panel opens
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 80);
    }
  }, [open]);

  const sendMessage = useCallback((text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isTyping) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: trimmed }]);
    setIsTyping(true);

    // 300ms delay — simulates Ayan "thinking"
    setTimeout(() => {
      const answer = respondToQuestion(trimmed);
      setIsTyping(false);
      setMessages((prev) => [...prev, { role: "ayan", text: answer }]);
    }, 300);
  }, [isTyping]);

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  // Whether suggestions should be visible: only after welcome message and no user turn yet
  const showSuggestions = messages.length === 1;

  return (
    <>
      {/* ── Floating action button ────────────────────────────────── */}
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label={open ? "Close Ask Ayan chat" : "Open Ask Ayan chat"}
        style={{
          position: "fixed",
          bottom: "2rem",
          right: "2rem",
          zIndex: 1000,
          width: 60,
          height: 60,
          borderRadius: "50%",
          background: "var(--primary)",
          color: "#fff",
          fontSize: "1.6rem",
          border: "none",
          cursor: "pointer",
          boxShadow: "0 4px 16px rgba(79,70,229,0.4)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          animation: open ? "none" : "askAyanPulse 2.5s ease-in-out infinite",
          transition: "transform 0.15s",
        }}
      >
        {open ? "✕" : "💬"}
      </button>

      {/* ── Chat panel ─────────────────────────────────────────────── */}
      {open && (
        <div
          style={{
            position: "fixed",
            bottom: "5.5rem",
            right: "2rem",
            zIndex: 1000,
            width: "min(380px, calc(100vw - 2rem))",
            maxHeight: "min(520px, calc(100vh - 8rem))",
            borderRadius: 14,
            background: "var(--surface)",
            border: "1px solid var(--border)",
            boxShadow: "0 8px 40px rgba(0,0,0,0.22)",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: "0.75rem 1rem",
              background: "var(--primary)",
              color: "#fff",
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              flexShrink: 0,
            }}
          >
            <span style={{ fontSize: "1.15rem" }}>🧠</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: "0.9rem", lineHeight: 1.3 }}>Ask Ayan</div>
              <div style={{ fontSize: "0.7rem", opacity: 0.8 }}>Portal questions only · no LLM involved</div>
            </div>
            <button
              onClick={() => setOpen(false)}
              aria-label="Close chat"
              style={{
                background: "rgba(255,255,255,0.15)",
                border: "none",
                color: "#fff",
                cursor: "pointer",
                fontSize: "0.85rem",
                padding: "0.2rem 0.5rem",
                borderRadius: 6,
                lineHeight: 1.5,
              }}
            >
              ✕
            </button>
          </div>

          {/* Messages */}
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "0.75rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.5rem",
            }}
          >
            {messages.map((msg, i) => (
              <div
                key={i}
                style={{
                  alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
                  maxWidth: "88%",
                }}
              >
                {msg.role === "ayan" && (
                  <div style={{ fontSize: "0.66rem", color: "var(--text-muted)", marginBottom: "0.2rem" }}>
                    🧠 Ask Ayan
                  </div>
                )}
                <div
                  style={{
                    padding: "0.5rem 0.75rem",
                    borderRadius:
                      msg.role === "user" ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
                    background: msg.role === "user" ? "var(--primary)" : "var(--bg)",
                    color: msg.role === "user" ? "#fff" : "var(--text)",
                    fontSize: "0.83rem",
                    lineHeight: 1.55,
                    border: msg.role === "ayan" ? "1px solid var(--border)" : "none",
                  }}
                >
                  {msg.role === "ayan" ? renderAnswer(msg.text) : msg.text}
                </div>

                {/* Suggestion chips: only after the welcome message */}
                {msg.role === "ayan" && i === 0 && showSuggestions && (
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: "0.35rem",
                      marginTop: "0.55rem",
                    }}
                  >
                    {SUGGESTIONS.map((s) => (
                      <button
                        key={s}
                        onClick={() => sendMessage(s)}
                        style={{
                          background: "rgba(79,70,229,0.08)",
                          border: "1px solid rgba(79,70,229,0.25)",
                          borderRadius: 999,
                          padding: "0.25rem 0.65rem",
                          fontSize: "0.75rem",
                          color: "var(--primary)",
                          cursor: "pointer",
                          fontFamily: "inherit",
                          fontWeight: 500,
                          lineHeight: 1.5,
                          transition: "background 0.12s",
                        }}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}

            {/* Typing indicator */}
            {isTyping && (
              <div style={{ alignSelf: "flex-start", maxWidth: "88%" }}>
                <div style={{ fontSize: "0.66rem", color: "var(--text-muted)", marginBottom: "0.2rem" }}>
                  🧠 Ask Ayan
                </div>
                <div
                  style={{
                    padding: "0.5rem 0.85rem",
                    borderRadius: "12px 12px 12px 2px",
                    background: "var(--bg)",
                    border: "1px solid var(--border)",
                    display: "flex",
                    gap: "0.3rem",
                    alignItems: "center",
                  }}
                >
                  <span className="ayan-dot" style={{ animationDelay: "0ms" }} />
                  <span className="ayan-dot" style={{ animationDelay: "160ms" }} />
                  <span className="ayan-dot" style={{ animationDelay: "320ms" }} />
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input bar */}
          <div
            style={{
              padding: "0.625rem 0.75rem",
              borderTop: "1px solid var(--border)",
              display: "flex",
              gap: "0.5rem",
              flexShrink: 0,
            }}
          >
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask a portal question…"
              disabled={isTyping}
              style={{
                flex: 1,
                padding: "0.4rem 0.65rem",
                borderRadius: 7,
                border: "1px solid var(--border)",
                background: "var(--bg)",
                color: "var(--text)",
                fontSize: "0.83rem",
                outline: "none",
                fontFamily: "inherit",
                opacity: isTyping ? 0.6 : 1,
              }}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={isTyping || !input.trim()}
              style={{
                padding: "0.4rem 0.8rem",
                borderRadius: 7,
                background: "var(--primary)",
                color: "#fff",
                border: "none",
                cursor: isTyping || !input.trim() ? "not-allowed" : "pointer",
                fontSize: "0.83rem",
                fontWeight: 600,
                opacity: isTyping || !input.trim() ? 0.55 : 1,
                transition: "opacity 0.12s",
              }}
            >
              Send
            </button>
          </div>
        </div>
      )}

      <style>{`
        @keyframes askAyanPulse {
          0%, 100% { box-shadow: 0 4px 16px rgba(79,70,229,0.4); }
          50%       { box-shadow: 0 4px 28px rgba(79,70,229,0.7), 0 0 0 8px rgba(79,70,229,0.12); }
        }
        @keyframes ayanDotBounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.35; }
          40%            { transform: translateY(-5px); opacity: 1; }
        }
        .ayan-dot {
          display: inline-block;
          width: 7px;
          height: 7px;
          border-radius: 50%;
          background: var(--primary);
          animation: ayanDotBounce 1.2s ease-in-out infinite;
        }
      `}</style>
    </>
  );
}

export default AskAyanChat;
