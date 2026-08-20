import React, { useState, useEffect, useRef, useCallback } from "react";
import { useSession } from "../context/SessionContext";
import { AskAyanChat } from "../components/Guide/AskAyanChat";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const NAV_H = 52; // px — must match App.tsx NavBar height

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
// Design atoms
// ---------------------------------------------------------------------------

function QuickReadCard({ text }: { text: string }) {
  const [collapsed, setCollapsed] = useState(false);
  return (
    <div
      style={{
        background: "rgba(79,70,229,0.07)",
        border: "1px solid rgba(79,70,229,0.22)",
        borderRadius: 10,
        padding: "1rem 1.25rem",
        marginBottom: "1.75rem",
      }}
    >
      <button
        onClick={() => setCollapsed((c) => !c)}
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          background: "none",
          border: "none",
          cursor: "pointer",
          width: "100%",
          padding: 0,
        }}
      >
        <span style={{ fontSize: "1.05rem" }}>⚡</span>
        <span style={{ fontWeight: 700, fontSize: "0.82rem", color: "var(--primary)", flex: 1, textAlign: "left" }}>
          2-MIN QUICK READ
        </span>
        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
          {collapsed ? "▶ expand" : "▼ collapse"}
        </span>
      </button>
      {!collapsed && (
        <p style={{ margin: "0.65rem 0 0 1.6rem", fontSize: "0.9rem", color: "var(--text)", lineHeight: 1.7 }}>
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
        fontSize: "1.45rem",
        fontWeight: 800,
        color: "var(--primary)",
        borderLeft: "4px solid var(--accent)",
        paddingLeft: "0.75rem",
        marginTop: 0,
        marginBottom: "0.4rem",
        lineHeight: 1.3,
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
        fontSize: "1rem",
        fontWeight: 700,
        color: "var(--text)",
        marginTop: "1.5rem",
        marginBottom: "0.4rem",
        borderBottom: "1px solid var(--border)",
        paddingBottom: "0.25rem",
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
        background: "rgba(124,58,237,0.06)",
        border: "1px solid rgba(124,58,237,0.2)",
        borderLeft: "3px solid var(--accent)",
        borderRadius: "0 8px 8px 0",
        padding: "0.7rem 1rem",
        margin: "1rem 0",
        fontSize: "0.875rem",
        color: "var(--text)",
        lineHeight: 1.65,
      }}
    >
      <span style={{ fontWeight: 700, color: "var(--accent)" }}>💡 Tip:&nbsp;</span>
      {children}
    </div>
  );
}

function Warning({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        background: "rgba(217,119,6,0.06)",
        border: "1px solid rgba(217,119,6,0.22)",
        borderLeft: "3px solid #d97706",
        borderRadius: "0 8px 8px 0",
        padding: "0.7rem 1rem",
        margin: "1rem 0",
        fontSize: "0.875rem",
        color: "var(--text)",
        lineHeight: 1.65,
      }}
    >
      <span style={{ fontWeight: 700, color: "#d97706" }}>⚠️ Note:&nbsp;</span>
      {children}
    </div>
  );
}

function AdminOnlyBanner() {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.5rem",
        padding: "0.4rem 0.75rem",
        marginBottom: "1rem",
        borderRadius: 6,
        background: "rgba(79,70,229,0.08)",
        border: "1px solid rgba(79,70,229,0.2)",
        fontSize: "0.78rem",
        color: "var(--primary)",
        fontWeight: 600,
      }}
    >
      🔐 This section is only visible to admin users.
    </div>
  );
}

function AdminBadgePill() {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        fontSize: "0.68rem",
        fontWeight: 700,
        padding: "0.1rem 0.45rem",
        borderRadius: 999,
        background: "rgba(79,70,229,0.12)",
        color: "var(--primary)",
        border: "1px solid rgba(79,70,229,0.25)",
        marginLeft: "0.45rem",
        verticalAlign: "middle",
        lineHeight: 1.5,
      }}
    >
      admin
    </span>
  );
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul
      style={{
        margin: "0.4rem 0 0.9rem 1.1rem",
        padding: 0,
        lineHeight: 1.75,
        fontSize: "0.9rem",
        color: "var(--text)",
      }}
    >
      {items.map((item, i) => (
        <li key={i} style={{ marginBottom: "0.3rem" }} dangerouslySetInnerHTML={{ __html: item }} />
      ))}
    </ul>
  );
}

function StepList({ steps }: { steps: string[] }) {
  return (
    <ol style={{ margin: "0.4rem 0 0.9rem 0", padding: 0, listStyle: "none", fontSize: "0.9rem" }}>
      {steps.map((step, i) => (
        <li
          key={i}
          style={{
            display: "flex",
            alignItems: "flex-start",
            marginBottom: "0.6rem",
            lineHeight: 1.65,
            color: "var(--text)",
          }}
        >
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: 22,
              height: 22,
              borderRadius: "50%",
              background: "var(--primary)",
              color: "#fff",
              fontSize: "0.72rem",
              fontWeight: 700,
              marginRight: "0.6rem",
              marginTop: "0.15rem",
              flexShrink: 0,
            }}
          >
            {i + 1}
          </span>
          <span dangerouslySetInnerHTML={{ __html: step }} />
        </li>
      ))}
    </ol>
  );
}

function TableRow({ label, value }: { label: string; value: string }) {
  return (
    <tr>
      <td
        style={{
          padding: "0.4rem 0.75rem",
          fontWeight: 600,
          fontSize: "0.85rem",
          color: "var(--text)",
          whiteSpace: "nowrap",
          verticalAlign: "top",
          borderBottom: "1px solid var(--border)",
        }}
        dangerouslySetInnerHTML={{ __html: label }}
      />
      <td
        style={{
          padding: "0.4rem 0.75rem",
          fontSize: "0.85rem",
          color: "var(--text-muted)",
          borderBottom: "1px solid var(--border)",
        }}
        dangerouslySetInnerHTML={{ __html: value }}
      />
    </tr>
  );
}

function SimpleTable({ rows }: { rows: { label: string; value: string }[] }) {
  return (
    <div style={{ overflowX: "auto", margin: "0.5rem 0 1rem" }}>
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          fontSize: "0.875rem",
          border: "1px solid var(--border)",
          borderRadius: 8,
          overflow: "hidden",
        }}
      >
        <tbody>
          {rows.map((r, i) => (
            <TableRow key={i} label={r.label} value={r.value} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section content
// ---------------------------------------------------------------------------

const gettingStartedContent = (
  <>
    <SubHeading>Your first time in the portal</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      Mastery Pulse works best when you follow the onboarding steps in order. Each step gives the system the
      signal it needs to personalise your experience.
    </p>
    <StepList
      steps={[
        "Go to the portal URL. Enter your <strong>email, name, role, practice area, and seniority level</strong> on the login screen. No password — just your identity.",
        "Navigate to <strong>My Profiles</strong> in the top nav bar.",
        "Click <em>Build a New Profile</em>. A short questionnaire helps the system recommend the best certification for your background and goals.",
        "Confirm the recommendation or pick a different certification from the catalog (Anthropic, AWS, Google Cloud, Microsoft, and more).",
        "Complete the <strong>self-assessment</strong>: rate yourself on the certification's key skills. Be honest — these scores set your initial baseline in the Domain Gap Chart.",
        "Click <em>Submit Assessment</em>. Your profile <strong>locks</strong>, the system computes your initial domain scores, and your Skill Radar populates.",
        "Two background tasks start automatically: quiz questions generate per skill (appears in the Quiz tab as ⏳), and byte-sized lessons start writing for your skill gaps.",
      ]}
    />
    <Warning>
      Your profile cannot be changed after it locks — this is intentional. Self-assessment is the starting
      baseline; only quiz answers move your scores from that point on. If you chose the wrong certification,
      create a new profile (you can have several, one per cert).
    </Warning>

    <SubHeading>What the system does with your data</SubHeading>
    <BulletList
      items={[
        "Self-assessment ratings are used <em>once</em> — to seed the Domain Gap Chart baseline. They play no further role after profile lock.",
        "Every quiz answer updates your Skill Radar (all questions) and the Domain Gap Chart (📋 Exam Relevant questions only).",
        "Your session is a server-side cookie. Nothing is stored in your browser's localStorage or sessionStorage.",
      ]}
    />

    <SubHeading>Coming back after a break</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      Re-enter your email on the login screen. The system recognises you and restores everything — profiles,
      quiz history, byte-sized lessons, and mock exam records — exactly where you left off.
    </p>

    <SubHeading>Multiple profiles</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      You can create one profile per certification you're targeting. Switch between them from the{" "}
      <strong>My Profiles</strong> page. The active profile badge in the nav bar shows your current cert code
      (e.g. <code>CCAR-P</code>). All tabs — Skill Radar, Quiz, Adoption Trends — reflect whichever profile
      is currently active.
    </p>
  </>
);

const skillRadarContent = (
  <>
    <SubHeading>Reading the radar</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      The Skill Radar is a polygon chart. Each spoke maps to one skill from your certification's exam blueprint.
      The dot on the spoke is your <strong>mastery score</strong> (0–100%). Further out = higher mastery. A
      fully-extended polygon means exam-ready across all skills.
    </p>
    <BulletList
      items={[
        "Nodes are <strong>colour-coded by exam-domain weight</strong> — dark blue for highest-weight domains, lighter blue for mid-range, grey for supplementary skills not directly tested.",
        "A <strong>domain legend</strong> below the radar maps each colour to its exam domain and weight percentage.",
        "Trend arrows (↑ green / ↓ amber) next to each node show whether that skill's score rose or fell since your last quiz round.",
      ]}
    />

    <SubHeading>Domain Gap Chart</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      The bar chart below the radar shows readiness <em>per exam domain</em>. This is the most direct answer to
      "am I ready for the real exam?"
    </p>
    <BulletList
      items={[
        "Bars move <strong>only</strong> from 📋 <em>Exam Relevant</em> quiz answers. 💡 <em>Good to Know</em> questions improve the radar but not the bars.",
        "If you see an amber badge '⚠️ Scores estimated', it means all LLM providers were busy when your profile was locked — your starting scores are mechanical estimates. They are replaced domain-by-domain as you answer quizzes.",
        "The chart is frozen to the exam domain <em>version</em> that was active when you locked your profile. An admin domain refresh only affects new profiles.",
      ]}
    />

    <SubHeading>What moves each score</SubHeading>
    <SimpleTable
      rows={[
        { label: "Skill Radar", value: "All quiz answers — both 📋 Exam Relevant and 💡 Good to Know." },
        {
          label: "Domain Gap Chart",
          value: "Only 📋 Exam Relevant quiz answers (questions tagged to the cert's official domains).",
        },
        {
          label: "Self-assessment",
          value: "Sets the Domain Gap Chart baseline at profile lock. Never changes scores afterward.",
        },
        {
          label: "Mock exams",
          value: "Diagnostic only — do NOT directly move the Skill Radar or Domain Gap Chart.",
        },
      ]}
    />
    <Tip>
      Focus quiz sessions on the 📋 Exam Relevant skill tabs first to move the Domain Gap Chart quickly. 💡
      Good to Know questions build broader conceptual depth but won't change your exam readiness score.
    </Tip>

    <SubHeading>Learning Journey</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      Beneath the Byte-Sized Learning table in the Skill Radar tab, the Learning Journey section shows your
      current learning path as an ordered roadmap — each skill in the sequence the system recommends. Click
      <em>Regenerate Path</em> to refresh the path based on your current mastery profile.
    </p>
  </>
);

const quizzesContent = (
  <>
    <SubHeading>How questions are generated</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      Questions are generated <strong>in the background</strong> right after your path is created — you never
      wait for them. Each skill gets its own AI call (1–2 questions each), so you can often start answering
      the first skill's questions while the rest are still generating.
    </p>
    <SimpleTable
      rows={[
        { label: "⏳ Pending (dimmed tab)", value: "Still generating — check back in a minute." },
        { label: "✅ Ready (normal tab)", value: "Questions available — dive in!" },
        {
          label: "⚠️ Failed (amber tab)",
          value: "Generation failed. A '↻ Retry Failed Skills' button appears at the top of the tab group.",
        },
      ]}
    />

    <SubHeading>The trap-reveal mechanic</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      Every wrong answer reveals a <strong>trap explanation</strong> — not just "the correct answer is B," but
      precisely why this answer <em>feels</em> right and isn't. This is the most valuable part of getting a
      question wrong. Don't skip it.
    </p>
    <Tip>
      After you answer a question incorrectly, the byte-sized lesson for that skill is rewritten to target the
      exact misconception you demonstrated — a personalised correction loop that closes the gap between "I got
      it wrong" and "I know why."
    </Tip>

    <SubHeading>Exam Relevant vs. Good to Know</SubHeading>
    <BulletList
      items={[
        "<strong>📋 Exam Relevant</strong> (blue badge): directly tests an official exam domain topic. Moves both your Skill Radar AND your Domain Gap Chart.",
        "<strong>💡 Good to Know</strong> (grey badge): builds conceptual depth but not on the exam blueprint. Moves Skill Radar only.",
        "Skill tabs are ordered: cert-domain skills first (with a coloured 'Exam' pill), supplementary skills below a divider.",
      ]}
    />

    <SubHeading>Answered questions log</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      At the bottom of each skill's quiz tab, a collapsible log lists every question you've already answered —
      your score, the correct answer, and the rationale. This is your revision reference; return to it any time.
    </p>

    <SubHeading>Automatic question refresh</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      Once all questions for a skill are answered, the system automatically generates new ones — harder if you
      scored well, easier if you struggled. Manually clicking <em>Regenerate Path</em> triggers a full refresh
      for all skills based on your current mastery.
    </p>

    <SubHeading>Retry failed skills</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      If any skill tab shows ⚠️ Failed, the <strong>↻ Retry Failed Skills</strong> button appears at the top of
      the quiz section. Click it to requeue generation for only the failed skills — already-ready skills are
      untouched.
    </p>
  </>
);

const byteSizedContent = (
  <>
    <SubHeading>What byte-sized lessons are</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      A byte-sized lesson is a short AI-generated micro-article (2–5 minutes) written specifically for your
      current skill gap. They appear in the <strong>Skill Radar tab</strong>, in a table above the Learning
      Journey section — one row per skill in your learning path.
    </p>

    <SubHeading>How lessons are personalised — priority order</SubHeading>
    <StepList
      steps={[
        "<strong>Wrong quiz answers (highest priority)</strong>: if you got a question wrong on this skill, the lesson targets the exact misconception you demonstrated — not a generic overview.",
        "<strong>Mastery gap (second priority)</strong>: if your score indicates a gap but you haven't answered questions yet, the lesson covers foundational or nuanced gaps implied by the score.",
        "<strong>Wrong mock exam answers (third priority)</strong>: questions you got wrong in a completed mock exam feed into the lesson for that skill.",
      ]}
    />
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      Each path regeneration creates fresh lessons calibrated to your current state. Old lessons move to a
      "Previous paths" section below a divider — nothing is discarded.
    </p>

    <SubHeading>Opening a lesson</SubHeading>
    <StepList
      steps={[
        "Click <strong>Read</strong> in the lesson row. The read modal opens with the full markdown content.",
        "A <strong>circular clock timer</strong> fills in as you read — it completes one revolution at the estimated read time (shown in minutes). The circle turns green when you've spent enough time.",
        "Click <strong>🔊 Read Aloud</strong> to have the lesson narrated. Choose your speed: 0.75× / 1× / 1.25× / 1.5× / 2×.",
        "Close the modal when done. The <strong>Time Spent</strong> column updates immediately.",
      ]}
    />

    <SubHeading>The '⚡ Read again' nudge</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      If you close the modal before spending at least 50% of the estimated read time, the table shows "⚡ Read
      again" in amber. This isn't a penalty — it's a gentle reminder that you may have skimmed something
      important. The content is always available; just click Read again.
    </p>

    <SubHeading>External links</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      At the bottom of each lesson, 3–5 curated links point to official documentation, reputable technical blog
      posts, or YouTube videos for deeper reading. They're type-labelled: 📝 Blog · 📖 Docs · 🎥 Video.
    </p>
    <Tip>
      The Read Aloud feature uses the browser's built-in Web Speech API — no external service, no API key,
      completely private. If Read Aloud isn't available in your browser, the button is hidden automatically.
    </Tip>
  </>
);

const mockExamContent = (
  <>
    <SubHeading>Starting an exam</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      Click <strong>Take Mock Exam</strong> from the Skill Radar tab. There's no mastery gate — you can take
      an exam on day one if you want to. If your aggregate mastery is below 40%, a soft advisory tip appears,
      but it won't prevent you from starting.
    </p>
    <Tip>
      Mock exam questions are weighted by the same domain percentages as the real certification exam. The system
      recycles unanswered questions from abandoned exams (no extra AI cost) and questions you got wrong before
      (up to 30% of each domain slot), so re-taking exams is never purely repetitive.
    </Tip>

    <SubHeading>During the exam</SubHeading>
    <BulletList
      items={[
        "A countdown timer shows time remaining. It keeps running even if you navigate away — the exam is paused, not abandoned.",
        "Each question shows <strong>instant feedback</strong> after you answer: correct answer, your choice, and a rationale.",
        "You can <strong>pause</strong> at any time. The timer resumes exactly where it left off when you return.",
        "The exam opens in a full browser tab. Closing the tab pauses the session.",
      ]}
    />

    <SubHeading>Abandoning an exam</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      Click <strong>Abandon</strong> (visible in the Mock Exam History table on your Adoption Trends tab) if
      you want to start fresh. You <strong>must provide a reason</strong> — this isn't just a safeguard.
      The system uses the abandoned session's unanswered questions in your next exam to save AI cost and give
      you questions you haven't seen yet.
    </p>

    <SubHeading>Mock Exam History</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      The <strong>Adoption Trends tab</strong> shows a full history table: date, certification, status
      (colour-coded), score %, questions answered vs total, time spent, and abandon reason where applicable.
      For your live session, an Abandon button appears with a required-reason dialog.
    </p>

    <SubHeading>Exam Confidence Score</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      Also on the Adoption Trends tab: a circular gauge showing your{" "}
      <strong>recency-weighted average score</strong> across all completed exams vs. the certification's
      passing threshold. More recent exams count more heavily. A trend arrow (↑ / ↓ / →) compares your last
      two completed exams. The <strong>🏅 Exam Ready</strong> badge appears when your weighted average meets
      or exceeds the passing score across at least 2 completed exams.
    </p>
  </>
);

const adoptionContent = (
  <>
    <SubHeading>The Adoption Trends tab</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      This tab (inside <em>My Dashboard</em>) has two main areas: your mastery progress chart and your nudge
      inbox. It also hosts the Mock Exam History table and Exam Confidence Score gauge (see the Mock Exams section above).
    </p>

    <SubHeading>Mastery progress chart</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      A line chart showing your mastery score history over time — one line per skill, or an aggregate trend.
      Use it to see which skills are improving and which are plateauing. The timeline updates every time you
      answer a quiz.
    </p>

    <SubHeading>Nudge inbox</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      Nudges are personalised messages your admin sends when they spot a gap between training progress and
      real-world adoption of what you've learned. They appear as cards in your inbox.
    </p>
    <BulletList
      items={[
        "If you have unread nudges, a count badge appears on the <em>Adoption Trends</em> tab label in the nav.",
        "Click a nudge card to open and read it. The unread count drops automatically.",
        "Nudges are <strong>not automated spam</strong>. An admin explicitly composed and sent each one to a specific group for a specific reason.",
        "The AI that drafts nudge messages never sees your name or individual scores — only aggregate patterns. The targeting is personalised; the message text is not.",
      ]}
    />
  </>
);

// ── Admin sections ──────────────────────────────────────────────────────────

const managingPractitionersContent = (
  <>
    <SubHeading>The practitioners list</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      The home page (/) shows all registered practitioners. Click any name to open their{" "}
      <strong>read-only profile</strong> — their Skill Radar, Activity summary, and profile details. You cannot
      edit their data or act on their behalf.
    </p>
    <BulletList
      items={[
        "Each row shows the practitioner's role, practice, and active certification code.",
        "A <strong>⛔ Deactivated</strong> badge appears next to the name if the account has been deactivated.",
      ]}
    />
    <Tip>
      If a practitioner reports quiz tabs stuck on ⏳ indefinitely, go to Observability and search{" "}
      <code>agent_name = 'quiz_batch_generator'</code> for their cert. If no rows exist, the background task
      never launched — use the practitioner's Retry Failed Skills button or the admin quiz-batch endpoint to
      re-trigger generation.
    </Tip>

    <SubHeading>Admin practitioner view — two tabs</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      Clicking a practitioner's name opens their profile at <code>/admin/practitioners/&lt;id&gt;</code>. There
      are two tabs:
    </p>
    <BulletList
      items={[
        "<strong>Skill Radar</strong> — the same radar and domain gap chart the practitioner sees. Read-only; no Regenerate or Edit controls visible.",
        "<strong>Activity</strong> — a summary of all observable engagement signals over time (see below).",
      ]}
    />
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      Leadership-role admins see both tabs but cannot deactivate accounts or access individual Observability data.
    </p>

    <SubHeading>Activity tab</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      The Activity tab shows all observable practitioner engagement in one screen — no need to cross-reference
      multiple pages. It has three sections:
    </p>
    <BulletList
      items={[
        "<strong>Summary cards</strong> (top row): Quiz Rounds · Overall Correct Rate · Total Lesson Time · Mock Exams Completed. One stat per card, bold and at a glance.",
        "<strong>Per-skill activity table</strong>: one row per skill in the practitioner's path. Columns: Skill · Mastery % (colour-coded green/amber/red) · Gap % · Quiz Rounds · Correct · Wrong · Correct % · Lesson Time. Sorted by gap descending — largest gaps first. Shows which skills need the most attention.",
        "<strong>Mock Exam History</strong>: all exam sessions newest-first. Shows date, cert, status, score %, questions answered / total, time spent, and abandon reason if applicable.",
      ]}
    />
    <SimpleTable
      rows={[
        { label: "Quiz Rounds", value: "Count of distinct days on which the practitioner answered at least one question for a given skill. More intuitive than raw attempt count." },
        { label: "Correct %", value: "Score 1.0 = correct. Score 0.0 = wrong. Partial scores rounded to nearest whole for display." },
        { label: "Lesson Time", value: "Sum of all closed read-session durations (lesson_reads.duration_seconds) across all path generations." },
        { label: "Gap %", value: "100 − Mastery %. Skills not yet answered show Gap = 100%." },
      ]}
    />

    <SubHeading>Deactivating an account</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      At the top of a practitioner's admin view, an <strong>"Deactivate Account"</strong> button (amber, outline)
      lets you block a practitioner's login. When clicked:
    </p>
    <StepList
      steps={[
        'A small inline confirmation appears: <em>&ldquo;Deactivate [Name]? They will not be able to log in until reactivated. All data is preserved. This action can be undone.&rdquo;</em>',
        "Click <strong>Deactivate</strong> to confirm. The button changes to <strong>Reactivate Account</strong> and a <strong>⛔ Deactivated</strong> badge appears in the profile panel.",
        "The practitioner's current session (if they are logged in) continues until it expires or they log out. Future login attempts are blocked with a clear message: <em>&ldquo;Your account has been deactivated — please contact your administrator.&rdquo;</em>",
        "To restore access, click <strong>Reactivate Account</strong> and confirm. Login is restored immediately.",
      ]}
    />
    <Warning>
      Deactivation is designed for leavers, role changes, or administrative holds — not discipline. All data
      (profiles, quiz history, lessons, exam sessions) is fully preserved. The practitioner can pick up exactly
      where they left off after reactivation. Only full admins (role = admin) can deactivate accounts;
      leadership-role admins do not see the button.
    </Warning>
  </>
);

const nudgeCampaignsContent = (
  <>
    <SubHeading>Campaign flow</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      All nudge campaigns are admin-initiated from the <strong>Nudges</strong> page. The flow has four stages:
    </p>
    <StepList
      steps={[
        "<strong>Generate Categories</strong>: Click the button. The AI analyses aggregate KPI data (no PII) and proposes up to 10 nudge categories — e.g. 'practitioners who completed self-assessment but have answered no quizzes in 14 days'.",
        "<strong>Preview Recipients</strong>: Select a category (or type a custom one). Pure Python logic resolves which practitioners match the criteria — no LLM involved at this step.",
        "<strong>Compose Message</strong>: The AI drafts a nudge message for this category + tone hint. You see the draft and a 'Tone check' assessment before anything is sent. Edit freely.",
        "<strong>Review & Send</strong>: Uncheck any practitioners you want to exclude. Click Send. Each practitioner gets one nudge row; it appears in their inbox immediately.",
      ]}
    />
    <Warning>
      The AI Nudge Composer never sees individual practitioner names or scores — only the category description,
      a tone hint, and the recipient count. Individual data is resolved after the LLM step. This is a
      deliberate privacy design, not a limitation. Do not attempt to include personal data in the category
      description field.
    </Warning>

    <SubHeading>Tone guidance</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      Nudges should be <strong>encouraging</strong>, not alarming or pressuring. The 'Tone check' field in the
      compose preview is your safety valve — read it before sending. A poorly-toned nudge can undermine
      practitioner trust more than no nudge at all. When in doubt, err toward the positive.
    </p>

    <SubHeading>Campaign history</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      Sent campaigns are listed on the Nudges page. Leadership-role admins can view campaign history but
      cannot initiate new campaigns.
    </p>
  </>
);

const certDomainContent = (
  <>
    <SubHeading>Why domain data is versioned</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      Certification exams change — AWS retired its ML Specialty exam, Anthropic added CCAR-P, Google Cloud
      revises domain weights quarterly. The portal stores domain definitions in{" "}
      <strong>versioned snapshots</strong> so a practitioner's scores are never retroactively shifted when a
      cert changes.
    </p>
    <BulletList
      items={[
        "Each practitioner's profile is frozen to the domain <em>version</em> that was current when they locked their profile.",
        "A new domain version only affects practitioners who create a new profile after the version is published.",
        "Old versions are never deleted — the portal always knows which version each profile uses.",
      ]}
    />

    <SubHeading>Running a domain refresh</SubHeading>
    <StepList
      steps={[
        "Go to <strong>Cert Domains</strong> in the nav bar.",
        "Select a certification and click <strong>Research Domains</strong>. The AI agent web-searches the official exam guide and proposes updated domain definitions.",
        "Review the proposal: domain names, weight percentages, and source confidence notes.",
        "<strong>Approve</strong> to publish a new version. <strong>Reject</strong> (with a note) to discard the proposal. Existing practitioner profiles are never affected by either action.",
      ]}
    />
    <Tip>
      Always spot-check the proposed domain names and weights against the official exam guide PDF before
      approving. The AI agent is generally reliable but can occasionally surface outdated or unofficial sources.
      High-confidence proposals (explicitly labelled) are safe to approve; medium and low-confidence proposals
      warrant a manual check.
    </Tip>

    <SubHeading>Adding a new certification</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      The domain discovery agent can propose certifications that don't yet exist in the catalog. Approving such
      a proposal creates a <code>certifications</code> row with <code>is_active = false</code>. The admin must
      separately activate the cert (via the certs API) before it becomes selectable by practitioners.
    </p>
  </>
);

const observabilityContent = (
  <>
    <SubHeading>What the agent_runs table shows</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      Every LLM call the system makes creates one row in the <strong>agent_runs</strong> table, visible on the
      Observability page.
    </p>
    <SimpleTable
      rows={[
        { label: "<code>agent_name</code>", value: "Which agent made the call — e.g. <code>quiz_batch_generator</code>, <code>byte_sized_lesson</code>, <code>domain_scorer</code>." },
        { label: "<code>model_used</code>", value: "Which LLM tier actually responded — Ultra, Lightning, or Haiku. Not the tier attempted first." },
        { label: "<code>status</code>", value: "<code>success</code> · <code>error</code> · <code>degraded</code>" },
        { label: "<code>input_tokens</code> / <code>output_tokens</code>", value: "Token usage for cost tracking." },
        { label: "<code>latency_ms</code>", value: "Wall-clock time including any tier fallback retries." },
      ]}
    />

    <SubHeading>Diagnosing stuck quiz generation</SubHeading>
    <StepList
      steps={[
        "Search agent_runs for <code>agent_name = 'quiz_batch_generator'</code> and the practitioner's cert code in the input JSON.",
        "If rows exist with <code>status = 'error'</code>: background task ran but failed. Check the error message field.",
        "If <strong>no rows exist</strong>: the background task never launched — likely an all-tiers timeout before the row was written. Use the practitioner's '↻ Retry Failed Skills' button.",
        "If <code>model_used = 'claude-haiku-4-5-20251001'</code> on calls that normally use NVIDIA: the circuit breaker has tripped. It resets after a 2-minute cooldown.",
      ]}
    />

    <SubHeading>Provider chain health</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      The system uses a three-tier call chain: NVIDIA Ultra (10 s) → NVIDIA Lightning (20 s) → Anthropic Haiku
      (20 s). If all three fail, the response is HTTP 503 and the UI shows an amber toast with a Retry button.
      After 5 consecutive complete NVIDIA failures, the <strong>circuit breaker</strong> trips and routes
      directly to Haiku for a 2-minute cooldown, then resets automatically.
    </p>
  </>
);

const adminUsersContent = (
  <>
    <SubHeading>Creating admin accounts</SubHeading>
    <p style={{ fontSize: "0.9rem", lineHeight: 1.7, color: "var(--text)" }}>
      Go to <strong>Admin Users</strong> in the nav (visible to full admins only — not leadership-role admins).
      Click <em>New Admin User</em> and fill in email, name, and role.
    </p>
    <BulletList
      items={[
        "New accounts are created with password <code>welcome</code> and a forced-change flag.",
        "On first login, the admin must change their password before reaching any data.",
        "Admins can change their own password at any time from the settings link.",
      ]}
    />

    <SubHeading>admin vs. leadership roles</SubHeading>
    <SimpleTable
      rows={[
        {
          label: "<strong>admin</strong>",
          value: "Full access: individual practitioner data, nudge campaigns, cert domains, observability, admin user management.",
        },
        {
          label: "<strong>leadership</strong>",
          value: "Practitioners list + sent campaign history only. Cannot see individual attempts, create campaigns, manage cert domains, or access observability.",
        },
      ]}
    />
    <Warning>
      Role enforcement is in API route middleware — a leadership-role session token cannot access admin-only
      endpoints even if the URL is known. It's not just a UI hide.
    </Warning>
  </>
);

// ---------------------------------------------------------------------------
// Section registry
// ---------------------------------------------------------------------------

function buildSections(isAdmin: boolean): Section[] {
  return [
    {
      id: "getting-started",
      emoji: "🚀",
      title: "Getting Started",
      quickRead:
        "Log in with your email (no password). Go to My Profiles → Build a New Profile → answer the certification questionnaire → complete your self-assessment → submit. The system generates your Skill Radar, queues quiz questions, and writes your first byte-sized lessons — all in the background. You can explore the portal while it works.",
      content: gettingStartedContent,
    },
    {
      id: "skill-radar",
      emoji: "🎯",
      title: "Your Skill Radar",
      quickRead:
        "The Skill Radar is a polygon chart where each spoke is a skill from your cert's exam blueprint. Mastery scores move only from quiz answers. The Domain Gap Chart below it tracks exam-specific readiness — driven only by 📋 Exam Relevant questions. Domain-coloured nodes show which skills carry the most exam weight.",
      content: skillRadarContent,
    },
    {
      id: "quizzes",
      emoji: "📝",
      title: "Quizzes",
      quickRead:
        "Questions are generated per-skill in the background right after your path is created. Each skill tab shows ⏳ Pending, ✅ Ready, or ⚠️ Failed. Wrong answers trigger a trap-reveal explanation — not just the right answer, but exactly why you went wrong. 📋 Exam Relevant questions move your Domain Gap Chart; 💡 Good to Know questions move the Skill Radar only.",
      content: quizzesContent,
    },
    {
      id: "byte-sized",
      emoji: "📖",
      title: "Byte-Sized Learning",
      quickRead:
        "Byte-Sized Learning shows targeted micro-articles (2–5 min each) in the Skill Radar tab. Lessons are written around your specific wrong answers first, then skill gaps, then mock exam errors. Open the read modal: circular timer tracks time, 🔊 Read Aloud plays at your chosen speed. '⚡ Read again' in amber means you closed it too soon.",
      content: byteSizedContent,
    },
    {
      id: "mock-exams",
      emoji: "🏆",
      title: "Mock Exams",
      quickRead:
        "Take a Mock Exam any time from the Skill Radar tab — no mastery gate required. Questions mirror the real exam's domain weighting, with instant per-question feedback. You can pause and resume. Abandoned exams' unanswered questions are recycled into your next exam at no extra AI cost. The Exam Confidence Score on Adoption Trends shows your recency-weighted average vs. the passing threshold.",
      content: mockExamContent,
    },
    {
      id: "adoption",
      emoji: "📈",
      title: "Adoption Trends & Nudges",
      quickRead:
        "The Adoption Trends tab shows your mastery history over time and your Nudge Inbox. Nudges are personalised messages from your admin — targeted when they spot a gap between training and real-world adoption. Unread nudges show a count on the tab label. The AI that drafts nudge messages never sees your name or individual scores.",
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
              "The home page (/) lists all practitioners. Click any name to open their admin view — two tabs: Skill Radar (read-only radar and domain gap chart) and Activity (summary cards + per-skill quiz/lesson stats + mock exam history). Full admins can Deactivate an account (login blocked, data preserved) or Reactivate it at any time.",
            content: managingPractitionersContent,
          },
          {
            id: "nudge-campaigns",
            emoji: "📣",
            title: "Nudge Campaigns",
            adminOnly: true,
            quickRead:
              "From Nudges: Generate Categories (AI analyses aggregate data, no PII) → Preview Recipients (Python resolves who qualifies) → Compose Message (AI drafts, you edit and review the Tone check) → Review & Send. Nudges arrive in practitioners' inboxes immediately.",
            content: nudgeCampaignsContent,
          },
          {
            id: "cert-domains",
            emoji: "📋",
            title: "Cert Domain Management",
            adminOnly: true,
            quickRead:
              "Exam domain definitions are versioned. Trigger the AI domain-refresh agent from the Cert Domains page. Review proposals and approve or reject. Approved versions only affect new profiles — existing profiles are frozen to the version active when they locked.",
            content: certDomainContent,
          },
          {
            id: "observability",
            emoji: "🔬",
            title: "Observability",
            adminOnly: true,
            quickRead:
              "The Observability page shows every LLM agent call: name, model tier used, status, token counts, latency. Use it to diagnose stuck quiz generation or check provider health. model_used = 'claude-haiku-4-5-20251001' on NVIDIA-mode calls means the circuit breaker fired.",
            content: observabilityContent,
          },
          {
            id: "admin-users",
            emoji: "🔑",
            title: "Admin Users",
            adminOnly: true,
            quickRead:
              "Create admin accounts from Admin Users (full admins only). New accounts use password 'welcome' with a forced change on first login. Two roles: admin (full access) and leadership (campaign history + practitioner list only). Role enforcement lives in API middleware, not just the UI.",
            content: adminUsersContent,
          },
        ]
      : []),
  ];
}

// ---------------------------------------------------------------------------
// Main page component
// ---------------------------------------------------------------------------

export default function GuidePage() {
  const { session } = useSession();
  const isAdmin = session?.identity_type === "admin";
  const sections = React.useMemo(() => buildSections(isAdmin), [isAdmin]);

  const [activeId, setActiveId] = useState(sections[0]?.id ?? "");
  const [sidebarOpen, setSidebarOpen] = useState(false); // mobile drawer
  const contentRef = useRef<HTMLDivElement>(null);

  // ── IntersectionObserver for sidebar active highlight ──────────────────
  // The body/viewport is the scroll container (NavBar is position:sticky at top:0).
  // rootMargin: "-52px" top offset accounts for the sticky nav bar height.
  const handleIntersect = useCallback(
    (entries: IntersectionObserverEntry[]) => {
      // Find the topmost visible section
      for (const entry of entries) {
        if (entry.isIntersecting) {
          setActiveId(entry.target.id);
          break;
        }
      }
    },
    [],
  );

  useEffect(() => {
    const observer = new IntersectionObserver(handleIntersect, {
      root: null, // viewport
      rootMargin: `-${NAV_H + 8}px 0px -60% 0px`,
      threshold: 0,
    });

    sections.forEach((s) => {
      const el = document.getElementById(s.id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [sections, handleIntersect]);

  // ── Navigation helpers ─────────────────────────────────────────────────
  const scrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      setActiveId(id);
      setSidebarOpen(false); // close drawer on mobile after pick
    }
  };

  // ── Render ─────────────────────────────────────────────────────────────
  return (
    <>
      {/* ── Mobile hamburger bar ───────────────────────────────────── */}
      <div
        style={{
          display: "none", // shown via CSS on small screens (see <style> below)
          position: "sticky",
          top: NAV_H,
          zIndex: 40,
          background: "var(--surface)",
          borderBottom: "1px solid var(--border)",
          padding: "0.5rem 1rem",
          alignItems: "center",
          gap: "0.75rem",
        }}
        className="guide-mobile-bar"
      >
        <button
          onClick={() => setSidebarOpen((o) => !o)}
          aria-label="Toggle guide navigation"
          style={{
            background: "none",
            border: "1px solid var(--border)",
            borderRadius: 6,
            padding: "0.3rem 0.55rem",
            cursor: "pointer",
            fontSize: "1rem",
            color: "var(--text)",
          }}
        >
          ☰
        </button>
        <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--primary)" }}>
          {sections.find((s) => s.id === activeId)?.emoji}{" "}
          {sections.find((s) => s.id === activeId)?.title ?? "Guide"}
        </span>
      </div>

      {/* ── Mobile sidebar overlay ─────────────────────────────────── */}
      {sidebarOpen && (
        <div
          onClick={() => setSidebarOpen(false)}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 45,
            background: "rgba(0,0,0,0.4)",
          }}
        />
      )}

      {/* ── Two-column layout ──────────────────────────────────────── */}
      <div
        ref={contentRef}
        style={{ display: "flex", minHeight: `calc(100vh - ${NAV_H}px)` }}
      >
        {/* ── Sidebar ────────────────────────────────────────────────── */}
        <aside
          className={`guide-sidebar${sidebarOpen ? " open" : ""}`}
          style={{
            width: 226,
            flexShrink: 0,
            borderRight: "1px solid var(--border)",
            background: "var(--surface)",
            // Sticky: stays visible as body scrolls.
            // top = navH so it sits flush under the sticky NavBar.
            position: "sticky",
            top: NAV_H,
            height: `calc(100vh - ${NAV_H}px)`,
            overflowY: "auto",
            overflowX: "hidden",
          }}
        >
          {/* Sidebar header */}
          <div
            style={{
              padding: "1.1rem 1rem 0.9rem",
              borderBottom: "1px solid var(--border)",
            }}
          >
            <div
              style={{
                fontWeight: 900,
                fontSize: "0.78rem",
                color: "var(--primary)",
                letterSpacing: "0.06em",
                textTransform: "uppercase",
              }}
            >
              📘 Mastery Pulse
            </div>
            <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: "0.15rem" }}>
              User Guide
            </div>
          </div>

          {/* Section nav */}
          <nav style={{ padding: "0.5rem 0" }}>
            {sections.map((s) => {
              const active = activeId === s.id;
              return (
                <button
                  key={s.id}
                  onClick={() => scrollTo(s.id)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.45rem",
                    width: "100%",
                    textAlign: "left",
                    padding: "0.45rem 1rem 0.45rem 0.85rem",
                    fontSize: "0.83rem",
                    fontWeight: active ? 700 : 400,
                    color: active ? "var(--primary)" : "var(--text-muted)",
                    background: active ? "rgba(79,70,229,0.09)" : "none",
                    border: "none",
                    borderLeft: active ? "3px solid var(--primary)" : "3px solid transparent",
                    cursor: "pointer",
                    transition: "background 0.12s, color 0.12s, border-color 0.12s",
                    fontFamily: "inherit",
                    lineHeight: 1.4,
                  }}
                >
                  <span style={{ opacity: 0.85 }}>{s.emoji}</span>
                  <span style={{ flex: 1 }}>{s.title}</span>
                  {s.adminOnly && <AdminBadgePill />}
                </button>
              );
            })}
          </nav>

          {/* Back to top */}
          <div style={{ padding: "0.75rem 1rem", borderTop: "1px solid var(--border)", marginTop: "0.5rem" }}>
            <button
              onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
              style={{
                fontSize: "0.75rem",
                color: "var(--text-muted)",
                background: "none",
                border: "none",
                cursor: "pointer",
                padding: 0,
                fontFamily: "inherit",
              }}
            >
              ↑ Back to top
            </button>
          </div>
        </aside>

        {/* ── Content ────────────────────────────────────────────────── */}
        <main
          style={{
            flex: 1,
            minWidth: 0,
            padding: "2.5rem clamp(1.25rem, 4vw, 3.5rem) 6rem",
            maxWidth: 820,
          }}
        >
          {/* Page header */}
          <div style={{ marginBottom: "2.75rem" }}>
            <h1
              style={{
                fontSize: "clamp(1.6rem, 4vw, 2.25rem)",
                fontWeight: 900,
                color: "var(--text)",
                margin: 0,
                lineHeight: 1.2,
              }}
            >
              Mastery Pulse Guide
            </h1>
            <p
              style={{
                fontSize: "0.95rem",
                color: "var(--text-muted)",
                marginTop: "0.6rem",
                lineHeight: 1.6,
              }}
            >
              Everything you need — from first login to exam day.
              {isAdmin && (
                <span style={{ marginLeft: "0.5rem", color: "var(--primary)", fontWeight: 600 }}>
                  Admin sections are included below.
                </span>
              )}
            </p>
            <div
              style={{
                marginTop: "1rem",
                padding: "0.6rem 0.9rem",
                borderRadius: 8,
                background: "rgba(79,70,229,0.06)",
                border: "1px solid rgba(79,70,229,0.15)",
                fontSize: "0.83rem",
                color: "var(--text-muted)",
              }}
            >
              💬 Got a quick question? Click the <strong>Ask Ayan</strong> button in the bottom-right corner
              for instant portal-specific answers.
            </div>
          </div>

          {/* Sections */}
          {sections.map((s, idx) => (
            <section
              key={s.id}
              id={s.id}
              style={{
                marginBottom: "3.75rem",
                scrollMarginTop: NAV_H + 16,
              }}
            >
              {/* Admin-only banner */}
              {s.adminOnly && <AdminOnlyBanner />}

              <SectionHeading>
                {s.emoji} {s.title}
              </SectionHeading>

              <QuickReadCard text={s.quickRead} />

              <div style={{ fontSize: "0.9rem", color: "var(--text)", lineHeight: 1.75 }}>
                {s.content}
              </div>

              {idx < sections.length - 1 && (
                <hr
                  style={{
                    marginTop: "3rem",
                    border: "none",
                    borderTop: "1px solid var(--border)",
                  }}
                />
              )}
            </section>
          ))}
        </main>
      </div>

      {/* ── Ask Ayan floating chat ─────────────────────────────────── */}
      <AskAyanChat />

      {/* ── Responsive styles ──────────────────────────────────────── */}
      <style>{`
        /* Show hamburger bar on small screens */
        @media (max-width: 700px) {
          .guide-mobile-bar { display: flex !important; }
          .guide-sidebar {
            position: fixed !important;
            top: 0 !important;
            left: -240px;
            height: 100vh !important;
            z-index: 46;
            transition: left 0.22s ease;
            box-shadow: 4px 0 20px rgba(0,0,0,0.15);
          }
          .guide-sidebar.open { left: 0 !important; }
        }
      `}</style>
    </>
  );
}
