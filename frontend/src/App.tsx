import { BrowserRouter, Link, NavLink, Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage";
import PractitionerPage from "./pages/PractitionerPage";
import RollupsPage from "./pages/RollupsPage";
import NudgesPage from "./pages/NudgesPage";

const navStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "1.5rem",
  padding: "0 1.5rem",
  height: "52px",
  background: "var(--surface)",
  borderBottom: "1px solid var(--border)",
  boxShadow: "var(--shadow)",
};

const brandStyle: React.CSSProperties = {
  fontWeight: 700,
  fontSize: "1rem",
  color: "var(--text)",
  textDecoration: "none",
  marginRight: "auto",
};

export default function App() {
  return (
    <BrowserRouter>
      <nav style={navStyle}>
        <Link to="/" style={brandStyle}>
          Mastery Pulse
        </Link>
        <NavLink
          to="/"
          end
          style={({ isActive }) => ({
            fontSize: "0.875rem",
            fontWeight: 500,
            color: isActive ? "var(--primary)" : "var(--text-muted)",
            textDecoration: "none",
          })}
        >
          Practitioners
        </NavLink>
        <NavLink
          to="/rollups"
          style={({ isActive }) => ({
            fontSize: "0.875rem",
            fontWeight: 500,
            color: isActive ? "var(--primary)" : "var(--text-muted)",
            textDecoration: "none",
          })}
        >
          Rollups
        </NavLink>
        <NavLink
          to="/nudges"
          style={({ isActive }) => ({
            fontSize: "0.875rem",
            fontWeight: 500,
            color: isActive ? "var(--primary)" : "var(--text-muted)",
            textDecoration: "none",
          })}
        >
          Nudges
        </NavLink>
      </nav>

      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/practitioners/:id/*" element={<PractitionerPage />} />
        <Route path="/rollups" element={<RollupsPage />} />
        <Route path="/nudges" element={<NudgesPage />} />
      </Routes>
    </BrowserRouter>
  );
}
