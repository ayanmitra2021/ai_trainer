import { useState, useRef, useEffect } from "react";

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
      "The **Skill Radar** is your learning command centre. It's a polygon chart where each spoke represents a skill from your chosen certification's blueprint. The further out the dot, the higher your mastery. Mastery scores move *only* from quiz answers — the radar is evidence-based, not self-reported. The **Domain Gap Chart** below it tracks exam-domain readiness separately, driven only by 'Exam Relevant' quiz questions.",
  },
  {
    keywords: ["quiz", "question", "generating", "pending", "baking", "failed", "retry", "item", "trap", "reveal"],
    answer:
      "Questions are generated **per-skill in the background** right after your learning path is created. Each skill tab shows one of three states: ⏳ Pending (still baking), ✅ Ready (dive in!), or ⚠️ Failed (hit the '↻ Retry Failed Skills' button). The **trap-reveal mechanic** is the secret sauce — each wrong answer reveals *why* you went wrong, not just the right answer. Questions tagged '📋 Exam Relevant' are directly from the exam blueprint and move your domain score; '💡 Good to Know' questions build understanding but don't affect exam readiness.",
  },
  {
    keywords: ["byte", "lesson", "micro", "read aloud", "tts", "speech", "timer", "read again"],
    answer:
      "**Byte-Sized Learning** shows up in your Skill Radar tab, above the Learning Journey. Each row is a targeted micro-article written for a specific skill gap. Click **Read** to open the modal — a circular timer tracks your reading time. Hit 🔊 **Read Aloud** to have the lesson read to you at your chosen speed (0.75× to 2×, just like YouTube). If you close the modal too quickly, you'll see '⚡ Read again' — the system noticed you didn't spend enough time. Lessons are regenerated fresh each time you regenerate your path.",
  },
  {
    keywords: ["mock exam", "mock", "exam", "abandon", "confidence", "pause", "resume", "timer", "confidence score", "exam ready"],
    answer:
      "You can take a **Mock Exam** any time from the Skill Radar tab (no 80% mastery gate). The exam simulates the real certification format — timed, domain-weighted, with instant per-question feedback. You can **pause** and come back later, or **abandon** it (with a reason). Abandoned sessions aren't wasted — their unanswered questions get recycled into your next exam at no extra LLM cost! The **Exam Confidence Score** on your Adoption Trends tab shows a recency-weighted average of all completed exams vs. the passing threshold. 'Exam Ready' 🏅 appears when you're consistently above the bar.",
  },
  {
    keywords: ["nudge", "inbox", "adoption", "trend", "adoption trends", "message", "unread"],
    answer:
      "The **Adoption Trends** tab shows two things: (1) your skill mastery trend over time, so you can see whether your scores are rising, and (2) your **Nudge Inbox**. Nudges are personalised messages your admin sends when they spot a gap between what you've learned and what shows up in your actual work. They arrive as cards in your inbox — unread ones show a count on the tab label. Click a nudge to mark it read.",
  },
  {
    keywords: ["profile", "certification", "cert", "domain", "assessment", "lock", "build profile", "self-assessment"],
    answer:
      "Your **Profile** is the foundation of everything. It starts with picking a certification — Anthropic, AWS, Google Cloud, Microsoft, or others. Then you rate yourself on the cert's key skills (this gives the system a starting baseline). Once you submit, your profile **locks** and the Domain Scorer maps your self-ratings to the cert's official exam domains. From that point, quiz answers are the only thing that changes your scores. You can have multiple profiles for different certs — switch between them from 'My Profiles' in the nav.",
  },
  {
    keywords: ["path", "learning path", "curriculum", "regenerate", "generate path", "journey"],
    answer:
      "Your **Learning Path** is the ordered list of skills the system thinks you should focus on, weighted toward your chosen certification's exam domains. It's generated automatically when you lock your profile and regenerated any time you click 'Regenerate Path'. Each generation also kicks off background tasks that write fresh quiz questions and byte-sized lessons for your current skill gaps.",
  },
  {
    keywords: ["admin", "observability", "agent run", "campaign", "nudge campaign", "cert domain", "practitioner list"],
    answer:
      "Admins have extra tools: **Observability** shows every LLM agent call (model used, latency, token count, status) — great for diagnosing stuck quizzes. **Cert Domains** lets you trigger the AI-powered domain-refresh agent and approve or reject its proposals. **Nudges** is the campaign tool — generate categories, preview who qualifies, compose a message, and send it. The LLM in the Nudge flow *never* sees individual practitioner names or scores — only aggregated counts.",
  },
  {
    keywords: ["login", "log in", "password", "account", "session", "email"],
    answer:
      "Practitioners log in with just their **email + name** — no password needed. If you've logged in before, the system recognises your email and restores your existing profile, quiz history, and progress automatically. Admins log in with an email + password (first-time password is 'welcome', and you'll be forced to change it on first login). Sessions are server-side cookies — nothing is stored in your browser.",
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
// Simple Markdown-like renderer (bold only — enough for this widget)
// ---------------------------------------------------------------------------
function renderAnswer(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return <span key={i}>{part}</span>;
  });
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
interface Message {
  role: "user" | "ayan";
  text: string;
}

const WELCOME: Message = {
  role: "ayan",
  text: "Hi! I'm Ayan's guide assistant 👋 Ask me anything about the Mastery Pulse portal — quizzes, skill radar, mock exams, byte-sized lessons, or admin features.",
};

export function AskAyanChat() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([WELCOME]);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to newest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    const userMsg: Message = { role: "user", text: trimmed };
    const ayanMsg: Message = { role: "ayan", text: respondToQuestion(trimmed) };
    setMessages((prev) => [...prev, userMsg, ayanMsg]);
    setInput("");
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <>
      {/* Floating action button */}
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="Ask Ayan"
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
        }}
      >
        {open ? "✕" : "💬"}
      </button>

      {/* Chat panel */}
      {open && (
        <div
          style={{
            position: "fixed",
            bottom: "5.5rem",
            right: "2rem",
            zIndex: 1000,
            width: 360,
            maxHeight: 480,
            borderRadius: 12,
            background: "var(--surface)",
            border: "1px solid var(--border)",
            boxShadow: "0 8px 32px rgba(0,0,0,0.25)",
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
            }}
          >
            <span style={{ fontSize: "1.1rem" }}>🧠</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: "0.9rem" }}>Ask Ayan</div>
              <div style={{ fontSize: "0.72rem", opacity: 0.8 }}>Portal questions only!</div>
            </div>
            <button
              onClick={() => setOpen(false)}
              style={{
                background: "none",
                border: "none",
                color: "#fff",
                cursor: "pointer",
                fontSize: "1rem",
                opacity: 0.75,
                padding: "0.1rem 0.3rem",
              }}
              aria-label="Close"
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
                  maxWidth: "85%",
                }}
              >
                {msg.role === "ayan" && (
                  <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginBottom: "0.15rem" }}>
                    🧠 Ayan
                  </div>
                )}
                <div
                  style={{
                    padding: "0.5rem 0.75rem",
                    borderRadius: msg.role === "user" ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
                    background: msg.role === "user" ? "var(--primary)" : "var(--bg)",
                    color: msg.role === "user" ? "#fff" : "var(--text)",
                    fontSize: "0.83rem",
                    lineHeight: 1.5,
                    border: msg.role === "ayan" ? "1px solid var(--border)" : "none",
                  }}
                >
                  {msg.role === "ayan" ? renderAnswer(msg.text) : msg.text}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div
            style={{
              padding: "0.625rem 0.75rem",
              borderTop: "1px solid var(--border)",
              display: "flex",
              gap: "0.5rem",
            }}
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask a portal question…"
              style={{
                flex: 1,
                padding: "0.4rem 0.6rem",
                borderRadius: 6,
                border: "1px solid var(--border)",
                background: "var(--bg)",
                color: "var(--text)",
                fontSize: "0.83rem",
                outline: "none",
              }}
            />
            <button
              onClick={send}
              style={{
                padding: "0.4rem 0.75rem",
                borderRadius: 6,
                background: "var(--primary)",
                color: "#fff",
                border: "none",
                cursor: "pointer",
                fontSize: "0.83rem",
                fontWeight: 600,
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
      `}</style>
    </>
  );
}

export default AskAyanChat;
