import RollupView from "../components/RollupView";

export default function RollupsPage() {
  return (
    <div style={{ maxWidth: 960, margin: "0 auto", padding: "2rem 1rem" }}>
      <h1>Leadership Rollups</h1>
      <p style={{ color: "var(--text-muted)", marginBottom: "1.5rem" }}>
        Aggregate adoption and mastery metrics by team or practice.
      </p>
      <RollupView />
    </div>
  );
}
