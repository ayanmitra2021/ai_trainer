import React from "react";
import { BrowserRouter, Link, NavLink, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { SessionProvider, useSession } from "./context/SessionContext";
import AdminPractitionerPage from "./pages/AdminPractitionerPage";
import HomePage from "./pages/HomePage";
import PractitionerPage from "./pages/PractitionerPage";
import NudgesPage from "./pages/NudgesPage";
import LoginPage from "./pages/LoginPage";
import ChangePasswordPage from "./pages/ChangePasswordPage";
import ObservabilityPage from "./pages/ObservabilityPage";
import AdminUsersPage from "./pages/AdminUsersPage";
import BuildProfilePage from "./pages/BuildProfilePage";
import ProfileSkillAssessmentPage from "./pages/ProfileSkillAssessmentPage";
import CertDomainManagementPage from "./pages/CertDomainManagementPage";
import MockExamPage from "./pages/MockExamPage";
import GuidePage from "./pages/GuidePage";
import NotificationConfigPage from "./pages/NotificationConfigPage";
import ProductAdminLoginPage from "./pages/ProductAdminLoginPage";
import ProductAdminPortal from "./pages/ProductAdminPortal";
import ProductAdminChangePasswordPage from "./pages/ProductAdminChangePasswordPage";
import { auth } from "./api";
import { PortalLayout } from "./components/PortalLayout";
import { ProviderUnavailableToast } from "./components/ProviderUnavailableToast/ProviderUnavailableToast";

const navStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "1.5rem",
  padding: "0 1.5rem",
  height: "52px",
  background: "var(--surface)",
  borderBottom: "1px solid var(--border)",
  boxShadow: "var(--shadow)",
  // Sticky nav — stays visible while GuidePage sidebar uses top: 52px
  position: "sticky",
  top: 0,
  zIndex: 50,
};

const brandStyle: React.CSSProperties = {
  fontWeight: 700,
  fontSize: "1rem",
  color: "var(--text)",
  textDecoration: "none",
  marginRight: "auto",
};

const navLinkStyle = ({ isActive }: { isActive: boolean }): React.CSSProperties => ({
  fontSize: "0.875rem",
  fontWeight: 500,
  color: isActive ? "var(--primary)" : "var(--text-muted)",
  textDecoration: "none",
});

function NavBar() {
  const { session, clear } = useSession();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await auth.logout();
    clear();
    navigate("/login");
  };

  // Product admins have their own sidebar nav — no shared NavBar
  if (!session || session.identity_type === "product_admin") return null;

  const isAdmin = session.identity_type === "admin";

  return (
    <nav style={navStyle}>
      <Link to="/" style={brandStyle}>
        Mastery Pulse
      </Link>

      {isAdmin && (
        <>
          <NavLink to="/" end style={navLinkStyle}>
            Practitioners
          </NavLink>
          <NavLink to="/nudges" style={navLinkStyle}>
            Nudges
          </NavLink>
          {session.admin_role === "admin" && (
            <>
              <NavLink to="/admin-users" style={navLinkStyle}>
                Admin Users
              </NavLink>
              <NavLink to="/observability" style={navLinkStyle}>
                Observability
              </NavLink>
              <NavLink to="/admin/cert-domains" style={navLinkStyle}>
                Cert Domains
              </NavLink>
            </>
          )}
          {/* Configure tab — enterprise admins only */}
          {session.plan_tier === "enterprise" && (
            <NavLink to="/admin/configure" style={navLinkStyle}>
              Configure
            </NavLink>
          )}
        </>
      )}

      {!isAdmin && (
        <>
          <NavLink to="/profile" style={navLinkStyle}>
            My Profiles
            {session.active_certification_code && (
              <span
                style={{
                  marginLeft: "0.4rem",
                  fontSize: "0.7rem",
                  padding: "0.1rem 0.4rem",
                  borderRadius: "999px",
                  background: "var(--primary)",
                  color: "#fff",
                  verticalAlign: "middle",
                }}
              >
                {session.active_certification_code}
              </span>
            )}
          </NavLink>
          <NavLink
            to={`/practitioners/${session.practitioner_id}/skills`}
            style={navLinkStyle}
          >
            My Dashboard
          </NavLink>
        </>
      )}

      {/* Guide — visible to all authenticated users */}
      <NavLink to="/guide" style={navLinkStyle}>
        Guide
      </NavLink>

      <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginLeft: "auto" }}>
        Hi, {session.first_name}
      </span>
      <button
        onClick={handleLogout}
        style={{
          fontSize: "0.8125rem",
          color: "var(--text-muted)",
          background: "none",
          border: "1px solid var(--border)",
          borderRadius: "4px",
          padding: "0.25rem 0.625rem",
          cursor: "pointer",
        }}
      >
        Log out
      </button>
    </nav>
  );
}

/** Redirect unauthenticated users to /login. */
function RequireAuth({ children }: { children: React.ReactNode }) {
  const { session, isLoading } = useSession();
  if (isLoading) return <div style={{ padding: "2rem", color: "var(--text-muted)" }}>Loading…</div>;
  if (!session) return <Navigate to="/login" replace />;
  if (session.identity_type === "admin" && session.must_change_password) {
    return <Navigate to="/change-password" replace />;
  }
  return <>{children}</>;
}

/** Redirect admin-only routes for non-admins. */
function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { session, isLoading } = useSession();
  if (isLoading) return null;
  if (!session || session.identity_type !== "admin") return <Navigate to="/login" replace />;
  return <>{children}</>;
}

/** Guard: only product_admin sessions pass through; others go to login. */
function RequireProductAdmin({ children }: { children: React.ReactNode }) {
  const { session, isLoading } = useSession();
  if (isLoading) return null;
  if (!session || session.identity_type !== "product_admin") {
    return <Navigate to="/product-admin/login" replace />;
  }
  if (session.must_change_password) {
    return <Navigate to="/product-admin/change-password" replace />;
  }
  return <>{children}</>;
}

/** Redirect practitioners to their profiles page (not the admin list). */
function PractitionerHome() {
  const { session } = useSession();
  if (session?.identity_type === "practitioner") {
    return <Navigate to="/profile" replace />;
  }
  return <HomePage />;
}

/** Root handler: redirects product_admin to their portal; others see PractitionerHome. */
function AppRoot() {
  const { session } = useSession();
  if (session?.identity_type === "product_admin") {
    return <Navigate to="/product-admin" replace />;
  }
  return <PractitionerHome />;
}

function AppRoutes() {
  return (
    <>
      <NavBar />
      {/* Phase 15.5: amber toast when all LLM providers return 503 */}
      <ProviderUnavailableToast />
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/change-password" element={<ChangePasswordPage />} />

        {/* Product Admin routes — completely separate from org-admin flow */}
        <Route path="/product-admin/login" element={<ProductAdminLoginPage />} />
        <Route path="/product-admin/change-password" element={<ProductAdminChangePasswordPage />} />
        <Route
          path="/product-admin/*"
          element={
            <RequireProductAdmin>
              <ProductAdminPortal />
            </RequireProductAdmin>
          }
        />

        {/* Authenticated routes with Portal Layout */}
        <Route
          path="/"
          element={
            <RequireAuth>
              <PortalLayout>
                <AppRoot />
              </PortalLayout>
            </RequireAuth>
          }
        />
        <Route
          path="/profile"
          element={
            <RequireAuth>
              <PortalLayout>
                <BuildProfilePage />
              </PortalLayout>
            </RequireAuth>
          }
        />
        <Route
          path="/profile/:profileId/skills"
          element={
            <RequireAuth>
              <PortalLayout>
                <ProfileSkillAssessmentPage />
              </PortalLayout>
            </RequireAuth>
          }
        />
        <Route
          path="/practitioners/:id/*"
          element={
            <RequireAuth>
              <PortalLayout>
                <PractitionerPage />
              </PortalLayout>
            </RequireAuth>
          }
        />
        <Route
          path="/nudges"
          element={
            <RequireAdmin>
              <PortalLayout>
                <NudgesPage />
              </PortalLayout>
            </RequireAdmin>
          }
        />
        <Route
          path="/admin-users"
          element={
            <RequireAdmin>
              <PortalLayout>
                <AdminUsersPage />
              </PortalLayout>
            </RequireAdmin>
          }
        />
        <Route
          path="/observability"
          element={
            <RequireAdmin>
              <PortalLayout>
                <ObservabilityPage />
              </PortalLayout>
            </RequireAdmin>
          }
        />
        {/* Step 9.2 — Admin/Leadership read-only practitioner view */}
        <Route
          path="/admin/practitioners/:id"
          element={
            <RequireAdmin>
              <PortalLayout>
                <AdminPractitionerPage />
              </PortalLayout>
            </RequireAdmin>
          }
        />

        {/* Phase 10 — Cert Domain Management */}
        <Route
          path="/admin/cert-domains"
          element={
            <RequireAdmin>
              <PortalLayout>
                <CertDomainManagementPage />
              </PortalLayout>
            </RequireAdmin>
          }
        />

        {/* Phase 22.10 — Enterprise notification configuration */}
        <Route
          path="/admin/configure"
          element={
            <RequireAdmin>
              <PortalLayout>
                <NotificationConfigPage />
              </PortalLayout>
            </RequireAdmin>
          }
        />

        {/* Interactive User Guide — Phase 20 */}
        <Route
          path="/guide"
          element={
            <RequireAuth>
              <PortalLayout>
                <GuidePage />
              </PortalLayout>
            </RequireAuth>
          }
        />

        {/* Mock Exam — opened in a new tab; no RequirePractitioner wrapper */}
        <Route path="/mock-exam/:sessionId" element={<MockExamPage />} />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <SessionProvider>
        <AppRoutes />
      </SessionProvider>
    </BrowserRouter>
  );
}
