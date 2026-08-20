import { useState, useEffect, useRef } from "react";
import { useSession } from "../context/SessionContext";
import { AskAyanChat } from "../components/Guide/AskAyanChat";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface Section {
  id: string;
  emoji: string;
  title: string;
  adminOnly?: boolean;
  quickRead: string;
  content: React.ReactNode;
}

// ---------------------------------------------------------------------------
// Small UI atoms
// ---------------------------------------------------------------------------

function QuickReadCard({ text }: { text: string }) {
  const [collapsed, setCollapsed] = useState(false);
  return (
    <div
      style={{
        background: "color-mix(in srgb, var(--primary) 8%, var(--surface))",
        border: "1px solid color-mix(in srgb, var(--primary) 25%, var(--border))",
        borderRadius: 10,
        padding: "1rem 1.25rem",
        marginBottom: "1.5rem",
      }}
    >
      <div
        style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}
        onClick={() => setCollapsed((c) => !c)}
      >
        <span style={{ fontSize: "1.1rem" }}>⚡</span>
        <span style={{ fontWeight: 700, fontSize: "0.85rem", color: "var(--primary)", flex: 1 }}>
          2-min quick read
        </span>
        <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{collapsed ? "▶ Expand" : "▼ Collapse"}</span>
      </div>
      {!collapsed && (
        <p style={{ margin: "0.6rem 0 0 1.6rem", fontSize: "0.9rem", color: "var(--text)", lineHeight: 1.65 }}>
          {text}
        </p>
      )}
    </div>
  );
}

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h2
      style={{
        fontSize: "1.4rem",
        fontWeight: 700,
        color: "var(--primary)",
        borderLeft: "4px solid var(--accent)",
        paddingLeft: "0.75rem",
        marginBottom: "0.5rem",
        marginTop: 0,
      }}
    >
      {children}
    </h2>
  );
}

function SubHeading({ children }: { children: React.ReactNode }) {
  return (
    <h3
      style={{
        fontSize: "1.05rem",
        fontWeight: 700,
        color: "var(--text)",
        marginTop: "1.25rem",
        marginBottom: "0.4rem",
      }}
    >
      {children}
    </h3>
  );
}

function Tip({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        background: "color-mix(in srgb, var(--accent) 8%, var(--surface))",
        border: "1px solid color-mix(in srgb, var(--accent) 20%, var(--border))",
        borderRadius: 8,
        padding: "0.75rem 1rem",
        margin: "0.75rem 0",
        fontSize: "0.875rem",
        color: "var(--text)",
        lineHeight: 1.6,
      }}
    >
      <span style={{ fontWeight: 700, color: "var(--accent)" }}>💡 Tip: </span>
      {children}
    </div>
  );
}

function AdminBadge() {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.25rem",
        fontSize: "0.72rem",
        fontWeight: 700,
        padding: "0.15rem 0.5rem",
        borderRadius: 999,
        background: "color-mix(in srgb, var(--primary) 15%, var(--surface))",
        color: "var(--primary)",
        border: "1px solid color-mix(in srgb, var(--primary) 30%, var(--border))",
        marginLeft: "0.5rem",
        verticalAlign: "middle",
      }}
    >
      🔐 Admin only
    </span>
  );
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul style={{ margin: "0.4rem 0 0.75rem 1.25rem", padding: 0, lineHeight: 1.7, fontSize: "0.9rem" }}>
      {items.map((item, i) => (
        <li key={i} style={{ marginBottom: "0.2rem" }} dangerouslySetInnerHTML={{ __html: item }} />
      ))}
    </ul>
  );
}

function StepBadge({ n }: { n: number }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: 24,
        height: 24,
        borderRadius: "50%",
        background: "var(--primary)",
        color: "#fff",
        fontSize: "0.75rem",
        fontWeight: 700,
        marginRight: "0.5rem",
        flexShrink: 0,
      }}
    >
      {n}
    </span>
  );
}

function StepList({ steps }: { steps: string[] }) {
  return (
    <ol style={{ margin: "0.4rem 0 0.75rem 0", padding: 0, listStyle: "none", fontSize: "0.9rem" }}>
      {steps.map((step, i) => (
        <li key={i} style={{ display: "flex", alignItems: "flex-start", marginBottom: "0.5rem", lineHeight: 1.6 }}>
          <StepBadge n={i + 1} />
          <span dangerouslySetInnerHTML={{ __html: step }} />
        </li>
      ))}
    </ol>
  );
}

// ---------------------------------------------------------------------------
// Section content
// ---------------------------------------------------------------------------

const gettingStartedContent = (
  <>
    <SubHeading>Your first time in the portal</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      Mastery Pulse works best when you go through the onboarding steps in order. Skip one and the system
      won't have the signal it needs to personalise your experience.
    </p>
    <StepList
      steps={[
        "Open the portal and enter your <strong>email, name, role, practice area, and seniority level</strong> on the login page. No password needed — just your identity.",
        "Navigate to <strong>My Profiles</strong> in the nav bar. Click <em>Build a New Profile</em>.",
        "A short questionnaire helps the system recommend the best certification for your background and goals. Read the recommendation, then confirm your choice or pick a different cert from the catalog.",
        "Complete the <strong>self-assessment</strong>: rate yourself on the certification's key skills. Be honest — these scores set your starting baseline in the Domain Gap Chart.",
        "Click <em>Submit Assessment</em>. Your profile locks, the system computes your initial domain scores, and your <strong>Skill Radar</strong> populates.",
        "The system kicks off two background tasks automatically: quiz questions start generating for each skill (appears in the Quiz tab as ⏳), and byte-sized lessons start writing for your top skill gaps.",
      ]}
    />
    <Tip>
      Your profile can't be changed after it locks — this is intentional. Your self-assessment is the baseline;
      from here, only quiz answers move your scores. If you chose the wrong certification, start a new profile
      (you can have multiple profiles for different certs).
    </Tip>

    <SubHeading>What the system does with your data</SubHeading>
    <BulletList
      items={[
        "Your self-assessment ratings are used <em>once</em> — to seed the Domain Gap Chart. They don't affect the Skill Radar from that point on.",
        "Every quiz answer updates both your Skill Radar (all questions) and the Domain Gap Chart (exam-relevant questions only).",
        "Your session lives in a server-side cookie. Nothing is stored in your browser's localStorage.",
      ]}
    />

    <SubHeading>Coming back after a break</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      Re-enter your email on the login page. The system recognises you and restores everything — your profiles,
      quiz history, byte-sized lessons, and mock exam records — exactly where you left off.
    </p>
  </>
);

const skillRadarContent = (
  <>
    <SubHeading>Reading the radar</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      Each spoke on the radar polygon maps to one skill from your certification's exam blueprint. The dot position
      on the spoke is your <strong>mastery score</strong> (0–100%). The further out the dot, the higher your
      mastery. A fully extended polygon means you're exam-ready across all skills.
    </p>
    <BulletList
      items={[
        "Nodes are <strong>colour-coded by exam-domain weight</strong>: dark blue for the highest-weight domains, lighter blue for mid-range, grey for supplementary skills not directly on the exam.",
        "A <strong>domain legend</strong> below the radar shows which colour maps to which exam domain (e.g. 'Enterprise Integration Patterns — 20%').",
        "Trend arrows (↑ green / ↓ amber) next to each node show whether that skill's score rose or fell since your last quiz round.",
      ]}
    />

    <SubHeading>Domain Gap Chart</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      The bar chart below the radar shows your readiness <em>per exam domain</em>, not per skill. This is the
      closest thing in the portal to "am I ready for the exam?"
    </p>
    <BulletList
      items={[
        "Bars are driven <strong>only by 'Exam Relevant' quiz answers</strong> — questions tagged 📋. 'Good to Know' questions improve the radar but don't move domain bars.",
        "If your profile was created when all LLM providers were busy, you'll see an amber badge: '⚠️ Scores estimated'. These are mechanical estimates — they get replaced domain-by-domain as you take quizzes.",
        "The domain gap chart freezes to the exam domain version that was active when you created your profile. If your admin refreshes the cert's domain data, your chart uses the old version; a new profile would use the new one.",
      ]}
    />

    <SubHeading>What moves your scores</SubHeading>
    <BulletList
      items={[
        "<strong>Skill Radar:</strong> all quiz answers (📋 Exam Relevant AND 💡 Good to Know).",
        "<strong>Domain Gap Chart:</strong> only 📋 Exam Relevant quiz answers.",
        "<strong>Self-assessment:</strong> sets initial Domain Gap Chart baseline at profile lock — never changes scores after that.",
        "<strong>Mock exams:</strong> do NOT directly move Skill Radar or Domain Gap Chart scores (they are diagnostic, not training).",
      ]}
    />

    <Tip>
      Focus your quiz sessions on the 📋 Exam Relevant tabs first if you want to move the Domain Gap Chart
      quickly. 💡 Good to Know questions are worth doing for broader conceptual depth but won't change your
      exam readiness score.
    </Tip>
  </>
);

const quizzesContent = (
  <>
    <SubHeading>How quiz generation works</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      Quiz questions are generated <strong>in the background</strong> after your path is created — the system
      doesn't make you wait. Each skill gets its own AI call (1–2 questions per skill), so you can often start
      answering the first skill's questions while the rest are still baking.
    </p>
    <BulletList
      items={[
        "<strong>⏳ Pending</strong> (dimmed tab): questions are being generated for this skill — check back in a minute.",
        "<strong>✅ Ready</strong> (normal tab): questions are available — dive in!",
        "<strong>⚠️ Failed</strong> (amber tab): generation failed for this skill. A <em>'↻ Retry Failed Skills'</em> button appears at the top — click it to try again.",
      ]}
    />

    <SubHeading>The trap-reveal mechanic</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      Every wrong answer reveals a <strong>trap explanation</strong> — a specific explanation of <em>why</em> this
      answer feels right but isn't. This isn't just "the correct answer is B" — it's "here's the misconception
      that makes A look attractive."
    </p>
    <Tip>
      The trap explanation is the most valuable part of getting a question wrong. Don't skip it. The byte-sized
      lesson for that skill will also be written to target the specific misconception you demonstrated — a
      personalised correction loop.
    </Tip>

    <SubHeading>Exam Relevant vs. Good to Know</SubHeading>
    <BulletList
      items={[
        "<strong>📋 Exam Relevant</strong> (blue badge): this question directly tests an official exam domain topic. Answering it moves both your Skill Radar AND your Domain Gap Chart.",
        "<strong>💡 Good to Know</strong> (grey badge): this question builds conceptual depth. It moves your Skill Radar but NOT the Domain Gap Chart.",
        "The skill tabs are ordered: cert-domain skills first (with a coloured 'Exam' pill), supplementary skills below a divider.",
      ]}
    />

    <SubHeading>Answered questions log</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      At the bottom of each skill's quiz tab, you'll find a collapsible log of every question you've already
      answered, with your score and the correct answer. This is your revision reference — you can return to it
      any time.
    </p>

    <SubHeading>Regenerating your path</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      Once you've answered all questions for a skill, the system refreshes that skill's questions automatically —
      harder ones if you scored well, easier ones if you struggled. You can also manually click{" "}
      <em>Regenerate Path</em> to get a fresh set based on your current mastery profile.
    </p>
  </>
);

const byteSizedContent = (
  <>
    <SubHeading>What byte-sized lessons are</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      Each lesson is a short, focused micro-article — typically 2–5 minutes — written by AI specifically for
      your current skill gap. They appear in the <strong>Skill Radar tab</strong>, in a table above the Learning
      Journey section. You'll see one row per skill in your learning path.
    </p>

    <SubHeading>How lessons are personalised</SubHeading>
    <BulletList
      items={[
        "<strong>If you got a quiz question wrong</strong> on this skill (first priority): the lesson targets the exact misconception you demonstrated — not a generic overview.",
        "<strong>If you have a mastery gap</strong> but no wrong answers yet (second priority): the lesson covers the foundational or nuanced gaps implied by your score.",
        "<strong>If you answered a mock exam question incorrectly</strong> for this skill (third priority): the lesson addresses that specific gap too.",
        "Each path regeneration creates fresh lessons calibrated to your current state — old lessons move to a 'Previous paths' section below a divider.",
      ]}
    />

    <SubHeading>Reading a lesson</SubHeading>
    <StepList
      steps={[
        "Click <strong>Read</strong> in the lesson row. The read modal opens with the full content.",
        "A <strong>circular clock timer</strong> fills in as you read — it completes one revolution at the estimated read time. It turns green when you've read long enough.",
        "Click <strong>🔊 Read Aloud</strong> to have the lesson read to you. Pick your speed: 0.75× / 1× / 1.25× / 1.5× / 2×.",
        "Close the modal when done. The <strong>Time Spent</strong> column updates immediately.",
      ]}
    />

    <SubHeading>The "⚡ Read again" nudge</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      If you close the modal before spending at least 50% of the estimated read time, the table shows "⚡ Read again"
      in amber. This isn't a penalty — it's a gentle reminder that you might have skimmed past something useful.
      The full content is always available; just click Read again.
    </p>

    <SubHeading>External links</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      At the bottom of each lesson, 3–5 curated links point to official documentation, reputable blog posts, or
      YouTube videos for deeper reading. Links are type-labelled: 📝 Blog, 📖 Docs, 🎥 Video.
    </p>
  </>
);

const mockExamContent = (
  <>
    <SubHeading>Starting an exam</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      Click <strong>Take Mock Exam</strong> from the Skill Radar tab. There's no mastery gate — you can take an
      exam at any point, even on day one. If your aggregate mastery is below 40%, a soft advisory tip appears, but
      it won't stop you.
    </p>
    <Tip>
      Mock exam questions are drawn from your certification's official domain blueprint — weighted by the same
      percentages as the real exam. The system recycles unanswered questions from abandoned exams (free!) and
      questions you got wrong before (up to 30% of each domain slot), so re-taking exams is never purely
      repetitive.
    </Tip>

    <SubHeading>During the exam</SubHeading>
    <BulletList
      items={[
        "A countdown timer shows time remaining. It keeps counting even if you navigate away — the exam is paused, not abandoned.",
        "Each question shows <strong>instant feedback</strong> after you answer: correct answer, your choice, and a rationale explaining why.",
        "You can <strong>pause</strong> the exam at any time and come back later. The timer resumes where it left off.",
        "The exam opens in a full browser tab — closing the tab pauses it.",
      ]}
    />

    <SubHeading>Abandoning an exam</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      If you want to start fresh, abandon the current exam. You <strong>must provide a reason</strong> — this isn't
      just a safeguard, it's data: the system uses abandoned sessions' unanswered questions in your next exam to
      reduce LLM calls and give you questions you haven't seen yet.
    </p>

    <SubHeading>Mock Exam History</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      The <strong>Adoption Trends tab</strong> has a full history table: date, certification, status
      (colour-coded), score %, questions answered vs total, time spent, and abandon reason if applicable. For
      your active session, an "Abandon" button appears in the table.
    </p>

    <SubHeading>Exam Confidence Score</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      Also on the Adoption Trends tab: a circular gauge showing your <strong>recency-weighted average score</strong>{" "}
      across all completed exams vs. the passing threshold. More recent exams count more. A trend arrow (↑/↓/→)
      compares your last two exams. The <strong>Exam Ready 🏅</strong> badge appears when your weighted average
      meets or exceeds the passing score across at least 2 completed exams.
    </p>
  </>
);

const adoptionContent = (
  <>
    <SubHeading>The Adoption Trends tab</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      This tab lives inside your practitioner dashboard and has two main sections: your mastery progress trend
      chart (how your skills have moved over time) and your nudge inbox.
    </p>

    <SubHeading>Mastery progress trend chart</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      A line chart showing your mastery score history over time — one line per skill, or an aggregate trend.
      Use this to see which skills are improving quickly and which are plateauing.
    </p>

    <SubHeading>Nudge inbox</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      Nudges are personalised messages your admin sends to practitioners when they spot a gap between training
      progress and real-world adoption. If you have unread nudges, a count appears on the Adoption Trends tab
      label in the nav.
    </p>
    <BulletList
      items={[
        "Click a nudge card to open and read it — the unread count drops automatically.",
        "Nudges are <strong>not automated spam</strong>. An admin explicitly composed and sent them to a specific group of practitioners for a specific reason.",
        "The LLM that helps write nudge messages never sees your name or individual data — only aggregate patterns. The personalisation is in the targeting, not the message text.",
      ]}
    />
  </>
);

// Admin sections
const managingPractitionersContent = (
  <>
    <SubHeading>The practitioners list</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      The home page (/) shows all registered practitioners. Click any name to open their read-only profile —
      you'll see their Skill Radar, domain gap chart, and learning path. You cannot edit their data or take
      actions on their behalf.
    </p>
    <BulletList
      items={[
        "Practitioners are listed with their role, practice area, and active certification (if any).",
        "You can filter and sort the list by name, practice, or certification.",
        "The Skill Radar you see for a practitioner is identical to what they see — read-only, no extra detail.",
      ]}
    />
    <Tip>
      If a practitioner reports that their quiz tabs are stuck on ⏳, check their learning path's quiz status
      in the Observability tab (agent_runs for 'quiz_batch_generator'). The retry endpoint resets failed skills.
    </Tip>
  </>
);

const nudgeCampaignsContent = (
  <>
    <SubHeading>How campaigns work</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      Nudge campaigns are admin-initiated. The flow has four stages:
    </p>
    <StepList
      steps={[
        "<strong>Generate Categories</strong>: Click the button on the Nudges page. The AI analyses aggregate KPI data (no individual PII) and proposes up to 10 nudge categories — e.g. 'practitioners who completed self-assessment but haven't taken any quizzes in 2 weeks'.",
        "<strong>Preview Recipients</strong>: Select a category (or type a custom one). The system resolves which practitioners match the criteria — purely Python logic, no LLM.",
        "<strong>Compose Message</strong>: The AI writes a draft nudge message for this category. You see the draft + a tone check before anything is sent. Edit freely.",
        "<strong>Review & Send</strong>: Uncheck any practitioners you want to exclude. Click Send. Each practitioner gets one nudge row; it appears in their inbox immediately.",
      ]}
    />
    <Tip>
      The AI Nudge Composer never sees individual practitioner names or scores — only the category description,
      a tone hint, and the recipient count. Individual practitioner data is resolved <em>after</em> the LLM step.
      This is a deliberate privacy design, not a limitation.
    </Tip>

    <SubHeading>Tone guidance</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      Nudges should be encouraging, not alarming. The AI prompt includes a self-check step (visible in the
      compose preview as "Tone check") — review it before sending. A poorly-toned nudge can do more harm than
      no nudge at all.
    </p>
  </>
);

const certDomainContent = (
  <>
    <SubHeading>Why domain data needs refreshing</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      Certification exam domains change — AWS retires exams, Anthropic adds new certs, Google Cloud revises
      domain weights. The portal stores domain data in versioned snapshots so a practitioner's scores are never
      retroactively shifted by a domain update.
    </p>

    <SubHeading>Running a domain refresh</SubHeading>
    <StepList
      steps={[
        "Go to <strong>Cert Domains</strong> in the nav bar.",
        "Select a certification and click <strong>Research Domains</strong>. The AI agent web-searches the official exam guide and proposes updated domain definitions.",
        "Review the proposal: domain names, descriptions, and weights. The agent includes confidence notes explaining where it found each data point.",
        "<strong>Approve</strong> to publish the new version (existing practitioner profiles are NOT affected — only new profiles use the new version). <strong>Reject</strong> with a note to discard the proposal.",
      ]}
    />
    <Tip>
      Always verify at least the domain names and weights against the official exam guide PDF before approving.
      The AI agent is good at this task but can occasionally surface outdated or unofficial sources. High-confidence
      proposals (explicitly labelled as such by the agent) are generally safe; medium and low-confidence proposals
      warrant a manual spot-check.
    </Tip>

    <SubHeading>Version semantics</SubHeading>
    <BulletList
      items={[
        "Each practitioner's profile is <strong>frozen to the domain version that was current when they locked their profile</strong>.",
        "A new domain version only affects practitioners who create a new profile after the approval.",
        "Old domain versions are never deleted — the portal always knows which version any given profile uses.",
      ]}
    />
  </>
);

const observabilityContent = (
  <>
    <SubHeading>The agent_runs table</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      Every LLM call made by the system is logged as one row in the <strong>agent_runs</strong> table, visible
      on the Observability page. Each row shows:
    </p>
    <BulletList
      items={[
        "<strong>agent_name</strong>: which agent made the call (e.g. 'quiz_batch_generator', 'byte_sized_lesson', 'domain_scorer').",
        "<strong>model_used</strong>: which LLM tier actually responded (Ultra, Lightning, or Haiku) — not the tier attempted first.",
        "<strong>status</strong>: 'success', 'error', or 'degraded'.",
        "<strong>input_tokens / output_tokens</strong>: token usage for cost tracking.",
        "<strong>latency_ms</strong>: wall-clock time for the call, including any tier retries.",
      ]}
    />

    <SubHeading>Diagnosing stuck quiz generation</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      If a practitioner reports their quiz tabs are stuck on ⏳ indefinitely:
    </p>
    <StepList
      steps={[
        "Check <strong>agent_runs</strong> for rows with agent_name = 'quiz_batch_generator' and the practitioner's cert code in the input JSON.",
        "If rows exist with status = 'error', the background task did run but failed. Check the error message.",
        "If <strong>no rows exist</strong>, the background task never launched — likely a model provider timeout that happened before the row was written.",
        "Use the <strong>Retry Failed Skills</strong> button (on the practitioner's Quiz tab) to requeue generation for failed skills.",
      ]}
    />

    <SubHeading>Provider chain health</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      The system uses a three-tier model chain: NVIDIA Ultra (10 s) → NVIDIA Lightning (20 s) → Anthropic Haiku
      (20 s). If all three fail, the response is an HTTP 503 and the UI shows an amber toast with a Retry button.
      If NVIDIA fails 5 times in a row, the circuit breaker trips and routes directly to Haiku for 2 minutes —
      visible in model_used as 'claude-haiku-4-5-20251001' on calls that normally use NVIDIA.
    </p>
  </>
);

const adminUsersContent = (
  <>
    <SubHeading>Creating admin accounts</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7 }}>
      Go to <strong>Admin Users</strong> in the nav bar (visible to full admins only, not leadership-role admins).
      Click <em>New Admin User</em>, fill in the email, name, and role (<strong>admin</strong> or{" "}
      <strong>leadership</strong>).
    </p>
    <BulletList
      items={[
        "New accounts are created with the password <code>welcome</code> and a forced-change flag.",
        "On first login, the admin must change their password before reaching any data view.",
        "Admins can change their own password at any time from the settings link in the nav.",
      ]}
    />

    <SubHeading>admin vs. leadership roles</SubHeading>
    <BulletList
      items={[
        "<strong>admin</strong>: full access — individual practitioner data, nudge campaigns, cert domains, observability, and admin user management.",
        "<strong>leadership</strong>: can view sent nudge campaign history and the practitioners list, but cannot see individual attempt data, create campaigns, or manage cert domains.",
      ]}
    />
    <Tip>
      The role distinction is enforced in API route middleware — a leadership-role token cannot access admin-only
      endpoints even if the URL is known. It's not just a UI hide.
    </Tip>
  </>
);

// ---------------------------------------------------------------------------
// All sections
// ---------------------------------------------------------------------------

function useSections(isAdmin: boolean): Section[] {
  return [
    {
      id: "getting-started",
      emoji: "🚀",
      title: "Getting Started",
      quickRead:
        "Log in with your email (no password for practitioners). Go to My Profiles → Build a New Profile → answer the certification questionnaire → complete your self-assessment → submit. The system then generates your Skill Radar, queues quiz questions, and writes your first byte-sized lessons — all in the background. You can start using the portal while that happens.",
      content: gettingStartedContent,
    },
    {
      id: "skill-radar",
      emoji: "🎯",
      title: "Your Skill Radar",
      quickRead:
        "The Skill Radar is a polygon chart where each spoke is a skill from your cert's exam blueprint. Mastery scores move only from quiz answers. The Domain Gap Chart below it tracks exam-specific readiness — driven only by 'Exam Relevant' (📋) questions. Domain-coloured nodes show which skills matter most for your exam.",
      content: skillRadarContent,
    },
    {
      id: "quizzes",
      emoji: "📝",
      title: "Quizzes",
      quickRead:
        "Questions are generated per-skill in the background right after your path is created. Each skill tab shows ⏳ Pending, ✅ Ready, or ⚠️ Failed. Wrong answers trigger a trap-reveal explanation that tells you exactly why you went wrong — not just what the right answer is. 📋 Exam Relevant questions move your Domain Gap Chart; 💡 Good to Know questions build the Skill Radar only.",
      content: quizzesContent,
    },
    {
      id: "byte-sized",
      emoji: "📖",
      title: "Byte-Sized Learning",
      quickRead:
        "Byte-Sized Learning shows targeted micro-articles (2–5 min each) in the Skill Radar tab. Lessons are written around your specific wrong answers first, then skill gaps, then mock exam errors. Click Read to open the lesson with a circular timer and 🔊 Read Aloud. '⚡ Read again' in amber means you closed it too quickly.",
      content: byteSizedContent,
    },
    {
      id: "mock-exams",
      emoji: "🏆",
      title: "Mock Exams",
      quickRead:
        "Take a Mock Exam any time from the Skill Radar tab — no mastery gate. Questions are weighted by exam domain, with instant per-question feedback. You can pause and resume. Abandoned exams' unanswered questions get recycled into your next exam (no extra AI cost). The Exam Confidence Score on Adoption Trends shows your recency-weighted average vs. the passing threshold.",
      content: mockExamContent,
    },
    {
      id: "adoption",
      emoji: "📈",
      title: "Adoption Trends & Nudges",
      quickRead:
        "The Adoption Trends tab shows your mastery history over time and your Nudge Inbox. Nudges are personalised messages from your admin — targeted at a specific gap pattern. Unread nudges show a count on the tab label. The AI that writes nudge messages never sees your name or individual scores.",
      content: adoptionContent,
    },
    ...(isAdmin
      ? [
          {
            id: "managing-practitioners",
            emoji: "👥",
            title: "Managing Practitioners",
            adminOnly: true,
            quickRead:
              "The home page lists all practitioners. Click any name to see their read-only Skill Radar, domain gap chart, and learning path. You cannot edit practitioner data. Use the Observability tab to diagnose stuck quiz generation.",
            content: managingPractitionersContent,
          },
          {
            id: "nudge-campaigns",
            emoji: "📣",
            title: "Nudge Campaigns",
            adminOnly: true,
            quickRead:
              "From the Nudges page: Generate Categories (AI analyses aggregate data) → Preview Recipients (Python resolves who qualifies) → Compose Message (AI drafts, you edit) → Review & Send. The LLM never sees individual practitioner names or scores. Nudges arrive in practitioners' inboxes immediately.",
            content: nudgeCampaignsContent,
          },
          {
            id: "cert-domains",
            emoji: "📋",
            title: "Cert Domain Management",
            adminOnly: true,
            quickRead:
              "Exam domain definitions are versioned. Trigger the AI domain-refresh agent to research and propose updated domains from official exam guides. Review and approve or reject proposals. Approved versions only affect new profiles — existing profiles are never retroactively shifted.",
            content: certDomainContent,
          },
          {
            id: "observability",
            emoji: "🔬",
            title: "Observability",
            adminOnly: true,
            quickRead:
              "The Observability page shows every LLM agent call: agent name, model tier used, status, token counts, latency. Use it to diagnose stuck quiz generation (look for quiz_batch_generator rows) or check provider health. model_used = 'claude-haiku-4-5-20251001' on NVIDIA-mode calls means the circuit breaker fired.",
            content: observabilityContent,
          },
          {
            id: "admin-users",
            emoji: "🔑",
            title: "Admin Users",
            adminOnly: true,
            quickRead:
              "Create admin accounts from the Admin Users page. New accounts use password 'welcome' with a forced change on first login. Two roles: admin (full access) and leadership (campaign history + practitioner list only). Role enforcement is in the API middleware, not just the UI.",
            content: adminUsersContent,
          },
        ]
      : []),
  ];
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export default function GuidePage() {
  const { session } = useSession();
  const isAdmin = session?.identity_type === "admin";
  const sections = useSections(isAdmin);

  const [activeId, setActiveId] = useState(sections[0]?.id ?? "");
  const contentRef = useRef<HTMLDivElement>(null);

  // Highlight sidebar item on scroll
  useEffect(() => {
    const container = contentRef.current;
    if (!container) return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
          }
        }
      },
      { root: container, rootMargin: "-20% 0px -70% 0px", threshold: 0 }
    );

    sections.forEach((s) => {
      const el = document.getElementById(s.id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [sections]);

  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      setActiveId(id);
    }
  };

  return (
    <div style={{ display: "flex", minHeight: "calc(100vh - 52px)", fontFamily: "inherit" }}>
      {/* ── Left sidebar ─────────────────────────────────────────────── */}
      <aside
        style={{
          width: 220,
          flexShrink: 0,
          borderRight: "1px solid var(--border)",
          background: "var(--surface)",
          padding: "1.5rem 0",
          position: "sticky",
          top: 52,
          height: "calc(100vh - 52px)",
          overflowY: "auto",
        }}
      >
        <div style={{ padding: "0 1rem 1rem", borderBottom: "1px solid var(--border)", marginBottom: "0.75rem" }}>
          <div style={{ fontWeight: 800, fontSize: "0.85rem", color: "var(--primary)", letterSpacing: "0.04em" }}>
            📘 MASTERY PULSE
          </div>
          <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: "0.2rem" }}>
            User Guide
          </div>
        </div>

        <nav>
          {sections.map((s) => (
            <button
              key={s.id}
              onClick={() => scrollTo(s.id)}
              style={{
                display: "block",
                width: "100%",
                textAlign: "left",
                padding: "0.45rem 1rem",
                fontSize: "0.83rem",
                fontWeight: activeId === s.id ? 700 : 400,
                color: activeId === s.id ? "var(--primary)" : "var(--text-muted)",
                background: activeId === s.id
                  ? "color-mix(in srgb, var(--primary) 10%, var(--surface))"
                  : "none",
                border: "none",
                borderLeft: activeId === s.id ? "3px solid var(--primary)" : "3px solid transparent",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
            >
              {s.emoji} {s.title}
              {s.adminOnly && (
                <span
                  style={{
                    display: "inline-block",
                    marginLeft: "0.3rem",
                    fontSize: "0.62rem",
                    padding: "0.1rem 0.35rem",
                    borderRadius: 999,
                    background: "color-mix(in srgb, var(--primary) 15%, var(--surface))",
                    color: "var(--primary)",
                    verticalAlign: "middle",
                    lineHeight: 1.4,
                  }}
                >
                  admin
                </span>
              )}
            </button>
          ))}
        </nav>
      </aside>

      {/* ── Right content pane ────────────────────────────────────────── */}
      <main
        ref={contentRef}
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "2.5rem 3rem 6rem",
          maxWidth: 780,
        }}
      >
        {/* Page header */}
        <div style={{ marginBottom: "2.5rem" }}>
          <h1 style={{ fontSize: "2rem", fontWeight: 800, color: "var(--text)", margin: 0 }}>
            Mastery Pulse Guide
          </h1>
          <p style={{ fontSize: "0.9rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
            Everything you need to get the most from the portal — from first login to exam day.
            {isAdmin && (
              <span style={{ marginLeft: "0.5rem", color: "var(--primary)", fontWeight: 600 }}>
                Admin sections are included below.
              </span>
            )}
          </p>
        </div>

        {sections.map((s) => (
          <section
            key={s.id}
            id={s.id}
            style={{
              marginBottom: "3.5rem",
              scrollMarginTop: "1.5rem",
            }}
          >
            <SectionHeading>
              {s.emoji} {s.title}
              {s.adminOnly && <AdminBadge />}
            </SectionHeading>

            <QuickReadCard text={s.quickRead} />

            <div style={{ fontSize: "0.9rem", color: "var(--text)", lineHeight: 1.7 }}>
              {s.content}
            </div>

            {/* Section divider */}
            <hr
              style={{
                marginTop: "2.5rem",
                border: "none",
                borderTop: "1px solid var(--border)",
              }}
            />
          </section>
        ))}
      </main>

      {/* ── "Ask Ayan" floating chat widget ──────────────────────────── */}
      <AskAyanChat />
    </div>
  );
}
