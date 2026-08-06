import { Link, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { usePractitioner } from "../hooks";
import SkillRadar from "../components/SkillRadar";
import QuizRunner from "../components/QuizRunner";
import TrendDashboard from "../components/TrendDashboard";

const TABS = [
  { path: "skills", label: "Skill Radar" },
  { path: "quiz", label: "Quiz" },
  { path: "trends", label: "Adoption Trends" },
] as const;

export default function PractitionerPage() {
  const { id = "" } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: person, isLoading } = usePractitioner(id);

  // Detect active tab from current pathname
  const activeTab = window.location.pathname.split("/").pop() ?? "skills";

  if (isLoading) {
    return (
      <div style={{ textAlign: "center", padding: "4rem" }}>
        <span className="spinner" />
      </div>
    );
  }

  if (!person) {
    return (
      <div style={{ maxWidth: 600, margin: "3rem auto", padding: "0 1rem" }}>
        <div className="card">
          <p>Practitioner not found.</p>
          <Link to="/">← Back to list</Link>
        </div>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 960, margin: "0 auto", padding: "2rem 1rem" }}>
      {/* Header */}
      <div style={{ marginBottom: "1.5rem" }}>
        <Link
          to="/"
          style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}
        >
          ← All practitioners
        </Link>
        <h1 style={{ marginTop: "0.5rem", marginBottom: "0.25rem" }}>
          {person.name}
        </h1>
        <p style={{ color: "var(--text-muted)", margin: 0, fontSize: "0.875rem" }}>
          {[person.email, person.role, person.practice, person.seniority_level]
            .filter(Boolean)
            .join(" · ")}
        </p>
      </div>

      {/* Tabs */}
      <div className="tabs">
        {TABS.map((t) => (
          <button
            key={t.path}
            className={`tab-btn${activeTab === t.path ? " active" : ""}`}
            onClick={() => navigate(`/practitioners/${id}/${t.path}`)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <Routes>
        <Route path="skills" element={<SkillRadar practitionerId={id} />} />
        <Route path="quiz" element={<QuizRunner practitionerId={id} />} />
        <Route
          path="trends"
          element={<TrendDashboard practitionerId={id} />}
        />
        {/* default */}
        <Route
          path="*"
          element={<SkillRadar practitionerId={id} />}
        />
      </Routes>
    </div>
  );
}
